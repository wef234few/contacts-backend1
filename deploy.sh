#!/bin/bash

# 安装函数计算命令行工具
# pip install aliyun-fun

# 打包代码
zip -r contacts-backend.zip . -x "venv/*" "*.db" "*.pyc" "__pycache__/*"

# 部署到函数计算
fun deploy