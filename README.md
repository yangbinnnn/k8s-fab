利用fabric + kubeadm 在Centos7 上快速搭建k8s 集群(单master)

```
curl https://bootstrap.pypa.io/get-pip.py | python # 安装pip
pip install fabric # 安装fabric
```

0. 配置Linux主机名, 注意主机名必须唯一!
```
hostname k8s-01 && hostname > /etc/hostname # on 192.168.1.101
hostname k8s-02 && hostname > /etc/hostname # on 192.168.1.102
hostname k8s-03 && hostname > /etc/hostanme # on 192.168.1.103
```

1. 配置部署操作机/etc/hosts
```
192.168.1.101 k8s-01
192.168.1.102 k8s-02
192.168.1.103 k8s-03
```

2. 配置集群/etc/hosts
```
fab -H k8s-01,k8s-02,k8s-03 config_hosts /etc/hosts
```

3. 配置集群yum源
```
fab -H k8s-01,k8s-02,k8s-03 aliyun_yum
```

4. 安装CRI, 使用Docker
```
fab -H k8s-01,k8s-02,k8s-03 install_docker
```

5. 安装k8s 套装
```
fab -H k8s-01,k8s-02,k8s-03 install_k8s
```

6. 初始化集群master, k8s-01 作为master
```
fab -H k8s-01 init_k8s_master
```

7. 加入node, k8s-02,k8s-3 作为node
```
fab -H k8s-02,k8s-03 join_k8s_cluster
```

8. 在master上安装网络插件
```
fab -H k8s-01 install_weavenet_master
```

9. 安装完成查看状态
```
fab -H k8s-01 -- "kubectl get nodes"

---
NAME     STATUS   ROLES    AGE    VERSION
k8s-01   Ready    master   9m    v1.13.4
k8s-02   Ready    <none>   5m    v1.13.4
k8s-03   Ready    <none>   5m    v1.13.4
```
