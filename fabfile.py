#!/usr/bin/env python
# encoding: utf-8
import os
import StringIO

from fabric import task

'''
- https://kubernetes.io/docs/setup/independent/create-cluster-kubeadm/
- run proxy api server:
export KUBECONFIG=/etc/kubernetes/admin.conf && kubectl proxy
'''

def k8s_version(c):
    output = c.run('kubelet --version').stdout
    output = output.strip()
    assert output.startswith('Kubernetes')
    return output.split()[1].strip()

@task
def config_hosts(c, hosts):
    assert os.path.exists(hosts), 'hosts file not found'
    c.put(hosts, '/etc/hosts')

@task
def check_env(c):
    cmds = [
        "hostname",
        "ip link",
        "lsmod | grep br_netfilter",
        "cat /proc/sys/net/bridge/bridge-nf-call-iptables"
    ]
    map(c.run, cmds)

@task
def aliyun_yum(c):
    k8s_yum = StringIO.StringIO("""
[kubernetes]
name=Kubernetes
baseurl=https://mirrors.aliyun.com/kubernetes/yum/repos/kubernetes-el7-x86_64/
enabled=1
gpgcheck=1
repo_gpgcheck=1
gpgkey=https://mirrors.aliyun.com/kubernetes/yum/doc/yum-key.gpg https://mirrors.aliyun.com/kubernetes/yum/doc/rpm-package-key.gpg
    """)
    c.put(k8s_yum, "/etc/yum.repos.d/kubernetes.repo")
    cmds = [
        "curl https://mirrors.aliyun.com/repo/Centos-7.repo > /etc/yum.repos.d/CentOS-Base.repo",
        "curl https://mirrors.aliyun.com/repo/epel-7.repo  > /etc/yum.repos.d/epel.repo",
        "yum clean all",
        "yum makecache -y",
        "yum update -y"
    ]
    map(c.run, cmds)

@task
def install_docker(c):
    cmds = [
        "yum install -y yum-utils device-mapper-persistent-data lvm2",
        "yum-config-manager --add-repo http://mirrors.aliyun.com/docker-ce/linux/centos/docker-ce.repo",
        "yum -y install docker-ce-18.06.2.ce",
        "mkdir -p /etc/docker"
    ]
    map(c.run, cmds)
    docker_conf = StringIO.StringIO("""
{
  "registry-mirrors": ["https://registry.docker-cn.com"],
  "exec-opts": ["native.cgroupdriver=systemd"],
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "100m"
  },
  "storage-driver": "overlay2",
  "storage-opts": [
    "overlay2.override_kernel_check=true"
  ]
}
    """)
    c.put(docker_conf, "/etc/docker/daemon.json")
    cmds = [
        "systemctl enable docker && systemctl restart docker"
    ]
    map(c.run, cmds)

@task
def install_k8s(c):
    k8s_sysctl = StringIO.StringIO("""
net.bridge.bridge-nf-call-ip6tables = 1
net.bridge.bridge-nf-call-iptables = 1
    """)
    c.put(k8s_sysctl, "/etc/sysctl.d/k8s.conf")
    cmds = [
        "sysctl --system",
        "setenforce 0",
        "sed -i 's/^SELINUX=enforcing$/SELINUX=permissive/' /etc/selinux/config",
        "yum install -y kubelet kubeadm kubectl --disableexcludes=kubernetes",
        "systemctl daemon-reload",
        "systemctl enable kubelet && systemctl restart kubelet"
    ]
    k8s_env = StringIO.StringIO("""
export KUBECONFIG=/etc/kubernetes/admin.conf
    """)
    c.put(k8s_env, "/etc/profile.d/k8s.sh")
    map(c.run, cmds)

@task
def init_k8s_master(c):
    ver = k8s_version(c)
    output = c.run("kubeadm init --kubernetes-version %s --image-repository registry.aliyuncs.com/google_containers" % ver)
    open('k8s_init.output', 'wb').write(output.stdout)

@task
def install_weavenet_master(c):
    c.run("""export KUBECONFIG=/etc/kubernetes/admin.conf && kubectl apply -f https://cloud.weave.works/k8s/net?k8s-version=$(kubectl version | base64 | tr -d '\n')""")
    c.run("sleep 3 && export KUBECONFIG=/etc/kubernetes/admin.conf && kubectl get pods --all-namespaces")

@task
def join_k8s_cluster(c):
    assert os.path.exists('k8s_init.output'), 'k8s_init.output not found, init-k8s-master first!'
    is_success = False
    join_cmd = ''
    for line in open('k8s_init.output'):
        line = line.strip()
        if 'Your Kubernetes master has initialized successfully' in line:
            is_success = True
            continue
        if line.startswith('kubeadm join') and ('--token' in line) and ('--discovery-token-ca-cert-hash' in line):
            join_cmd = line
            continue
    assert is_success, 'init_k8s_master not success, cat k8s_init.output for detail'
    assert join_cmd, 'cluster join cmd not found, cat k8s_init.output for detail'
    print 'join_cmd:', join_cmd
    c.run(join_cmd)
