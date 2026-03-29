# django_pos_system1656
本地小型pos收银系统


# 零售店POS收银系统 - 技术文档

## 1. 项目概述

本项目是一个基于Django开发的B/S架构零售店POS收银系统，面向中小型零售店，提供完整的商品管理、销售收银、会员管理、库存预警和报表统计功能。

**核心功能：**
- 商品管理（分类、信息维护、库存管理）
- 销售收银（条码查询、购物车、多支付方式）
- 会员管理（积分、余额、消费记录）
- 库存预警（低库存提醒、过期提醒）
- 报表统计（销售趋势、商品分析、报表打印）
- 系统设置（数据备份、参数配置）

**用户角色：**
- 管理员（admin）：完整权限
- 店长（manager）：管理权限
- 收银员（cashier）：收银权限

## 2. 技术栈

| 类别 | 技术/框架 | 版本 | 说明 |
|------|----------|------|------|
| 后端 | Python | 3.9+ | 核心编程语言 |
| 后端框架 | Django | 4.2 | Web应用框架 |
| 数据库 | MySQL | 8.0+ | 数据存储 |
| 前端 | HTML5/CSS3 | - | 页面结构与样式 |
| 前端框架 | Bootstrap 5 | - | 响应式UI组件 |
| 前端交互 | JavaScript/Ajax | - | 异步数据交互 |
| 图表库 | ECharts | 5.4.3 | 数据可视化 |
| 图像处理 | Pillow | - | 商品图片处理 |
| 数据库驱动 | mysqlclient/SQLite | - | MySQL连接 |

## 3. 项目结构

```
pos_system/
├── manage.py              # Django管理脚本
├── pos_system/           # 项目配置目录
│   ├── settings.py       # 项目设置
│   ├── urls.py           # 主路由配置
│   ├── wsgi.py           # WSGI服务器配置
│   └── __init__.py       # 初始化文件
├── users/                # 用户与权限管理
│   ├── models.py         # 用户模型
│   ├── views.py          # 用户相关视图
│   ├── urls.py           # 用户路由
│   ├── decorators.py     # 权限装饰器
│   └── templates/        # 用户相关模板
├── products/             # 商品管理
│   ├── models.py         # 商品、分类模型
│   ├── views.py          # 商品相关视图
│   ├── urls.py           # 商品路由
│   └── templates/        # 商品相关模板
├── sales/                # 销售收银
│   ├── models.py         # 订单、挂单模型
│   ├── views.py          # 销售相关视图
│   ├── urls.py           # 销售路由
│   └── templates/        # 销售相关模板
├── members/              # 会员管理
│   ├── models.py         # 会员模型
│   ├── views.py          # 会员相关视图
│   ├── urls.py           # 会员路由
│   └── templates/        # 会员相关模板
├── reports/              # 报表统计
│   ├── views.py          # 报表相关视图
│   ├── urls.py           # 报表路由
│   └── templates/        # 报表相关模板
├── system/               # 系统设置
│   ├── models.py         # 系统配置模型
│   ├── views.py          # 系统相关视图
│   ├── urls.py           # 系统路由
│   ├── backup_scheduler.py # 备份调度
│   └── templates/        # 系统相关模板
├── templates/            # 公共模板
│   └── public/           # 基础模板
├── static/               # 静态文件
├── media/                # 媒体文件（商品图片）
├── backups/              # 数据备份
├── resource/             # 项目资源
└── venv/                 # 虚拟环境
```

## 4. 技术实现

### 4.1 核心模型设计

**User模型**（自定义用户模型）
- 扩展Django默认User，添加role字段区分用户角色
- 支持基于角色的权限控制

**Product模型**
- 包含商品基本信息：条形码、名称、分类、价格、成本、库存
- 新增保质期（shelf_life）和过期时间（expiry_date）字段
- 支持库存预警功能

**Order模型**
- 订单主表：订单号、收银员、会员、总金额、支付方式
- OrderItem子表：订单明细，记录商品、数量、单价

**Member模型**
- 会员信息：卡号、姓名、手机、积分、余额
- 支持积分和余额支付

**StockLog模型**
- 库存变动日志：记录商品入库、出库、盘点等操作
- 包含变动类型、数量、变动前后库存

### 4.2 关键技术点

**权限控制**
- 基于装饰器的权限检查（@login_required, @manager_required）
- 不同角色访问不同功能模块

**异步交互**
- 使用Ajax实现无刷新数据交互
- 购物车管理、库存检查、实时统计

**数据安全**
- 事务性操作确保数据一致性
- 库存扣减与订单创建原子操作

**报表统计**
- ECharts实现销售趋势和商品分析图表
- 支持按时间周期查询

**过期提醒**
- 仪表盘显示一个月内即将过期的商品
- 按过期时间升序排序

**数据备份**
- 自动备份功能
- 支持手动备份和恢复

## 5. 核心功能模块

### 5.1 商品管理
- 商品分类：支持多级分类
- 商品信息：基本信息、价格、库存、保质期
- 库存管理：实时库存、库存变动日志
- 库存预警：低库存提醒、过期提醒

### 5.2 销售收银
- 商品扫描：支持条形码扫描
- 购物车：添加、修改、删除商品
- 挂单/取单：临时保存购物车
- 支付方式：现金、微信、支付宝、会员卡
- 订单打印：销售小票

### 5.3 会员管理
- 会员信息：基本资料、积分、余额
- 消费记录：历史消费明细
- 积分管理：消费积分、积分兑换
- 余额管理：充值、消费

### 5.4 报表统计
- 销售趋势：按日、周、月统计
- 商品分析：畅销商品、毛利分析
- 会员分析：会员消费、活跃度

### 5.5 系统设置
- 数据备份：自动备份配置
- 系统参数：系统名称、验证码设置
- 用户管理：添加、修改、删除用户

## 6. 快速开始

### 6.1 环境搭建

```bash
# 1. 克隆项目后进入目录
cd pos_system

# 2. 创建虚拟环境
python -m venv venv

# 3. 激活虚拟环境
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 4. 安装依赖
pip install -r requirements.txt

# 5. 补充设置文件
# 编辑 pos_system/settings.py 中的 os.environ.get 相关配置，改成你自己的，数据库名称默认用db.sqlite3

# 6. 执行数据库迁移
python manage.py makemigrations
python manage.py migrate

# 7. 创建超级用户
python manage.py createsuperuser

# 8. 启动开发服务器
python manage.py runserver

# 9. 启动后需要保持网络通常，因为前端框架直接引用了CDN在线资源

python manage.py runserver

```

### 6.2 访问系统
- 管理后台：http://localhost:8000/admin/
- 系统首页：http://localhost:8000/

## 7. 部署说明

### 7.1 生产环境部署

**使用Gunicorn + Nginx**

```bash
# 安装Gunicorn
pip install gunicorn

# 启动Gunicorn
gunicorn pos_system.wsgi:application --bind 0.0.0.0:8000

# 配置Nginx反向代理
# 参考Nginx配置示例：
# server {
#     listen 80;
#     server_name example.com;
#     
#     location / {
#         proxy_pass http://127.0.0.1:8000;
#         proxy_set_header Host $host;
#         proxy_set_header X-Real-IP $remote_addr;
#     }
#     
#     location /static/ {
#         alias /path/to/pos_system/static/;
#     }
#     
#     location /media/ {
#         alias /path/to/pos_system/media/;
#     }
# }
```

### 7.2 打包部署

**使用PyInstaller打包**

```bash
# 安装PyInstaller
pip install pyinstaller

# 执行打包
pyinstaller run.spec

# 打包结果位于 dist/run 目录
# 运行 dist/run/run.exe 启动系统
```

## 8. 注意事项

1. **数据库版本**：必须使用MySQL 8.0或更高版本（Django 4.2要求）
2. **虚拟环境**：建议使用venv隔离项目环境
3. **权限设置**：首次登录后创建不同角色的用户
4. **数据备份**：定期备份数据库，避免数据丢失
5. **静态文件**：生产环境需配置静态文件服务
6. **安全设置**：生产环境需修改SECRET_KEY和DEBUG设置

## 9. 开发指南

### 9.1 代码规范
- 遵循PEP 8代码规范
- 视图函数使用装饰器进行权限控制
- 模板使用Bootstrap 5组件保持一致性

### 9.2 新增功能
1. 在对应应用的models.py中定义模型
2. 执行makemigrations和migrate
3. 在views.py中实现业务逻辑
4. 在urls.py中配置路由
5. 在templates中创建前端页面
6. 添加必要的JavaScript交互逻辑

### 9.3 调试技巧
- 使用Django Admin进行数据管理
- 查看控制台日志和网络请求
- 使用Django的调试工具栏（django-debug-toolbar）

## 10. 联系方式

- 项目维护：开发团队
- 技术支持：如有问题请联系开发人员
- 版本更新：定期更新功能和修复bug

---

**版本：1.0.0**
**最后更新：2026-03-19**
