# LSEG自动化程序配置说明

## 📁 配置文件：config.cnf

### 🔐 账户配置

**LSEG登录账户**
```ini
[lseg_login]
username = ian.zhu@lseg.com
password = Welcome802
```

**SFTP服务器配置**
```ini
[sftp]
host = 192.168.0.117
username = ian
password = 3000xtra
remote_dir = /home/ian/ricchange
```

**163邮箱配置**
```ini
[email]
smtp_server = smtp.163.com
smtp_port = 587
sender = cbible@163.com
password = 3000xtra
recipient = ian.zhu@lseg.com
enable_email = true
```

### 📂 文件路径配置

```ini
[paths]
downloads_path = C:/Users/jacky/Downloads
target_dir = c:/ric_change
target_file = DownloadRicChangeEvents.xlsx
```

## 🛠️ 使用说明

1. **修改配置**：直接编辑 `config.cnf` 文件中的参数
2. **运行程序**：`python lseg_login_simple.py`
3. **安全性**：config.cnf已添加到.gitignore，不会被提交到版本控制

## 📧 163邮箱设置

如果邮件发送失败，请检查：

1. **开启SMTP服务**
   - 登录163邮箱
   - 设置 → 客户端授权密码
   - 开启SMTP服务

2. **获取授权码**
   - 生成客户端授权密码
   - 将授权码替换config.cnf中的password

3. **防火墙检查**
   - 确保端口587未被阻止
   - 检查网络连接

## 🔄 快速替换账户

只需修改config.cnf中对应的账户信息即可：
- LSEG账户：修改[lseg_login]部分
- SFTP账户：修改[sftp]部分  
- 邮箱账户：修改[email]部分

## ⚠️ 注意事项

- 请勿将config.cnf提交到公共代码库
- 密码包含特殊字符时请用引号包围
- 路径使用正斜杠/或双反斜杠\\ 