# Gmail邮件发送配置指南

## 1. 启用Gmail两步验证

1. 访问 [Google账户安全设置](https://myaccount.google.com/security)
2. 点击"两步验证"
3. 按照提示启用两步验证

## 2. 生成应用专用密码

1. 访问 [应用专用密码页面](https://myaccount.google.com/apppasswords)
2. 选择"邮件"应用和你的设备
3. 点击"生成"
4. 记录生成的16位密码（格式如：abcd efgh ijkl mnop）

## 3. 配置脚本

在 `lseg_login_simple.py` 中修改以下配置：

```python
# 邮件配置
self.email_sender = "你的Gmail地址@gmail.com"
self.email_password = "16位应用专用密码"  # 不要包含空格
self.enable_email = True  # 启用邮件发送
```

## 4. 测试邮件发送

运行程序后，如果看到以下信息说明配置成功：
- ✅ 邮件发送成功！

如果失败，请检查：
- Gmail地址是否正确
- 应用专用密码是否正确（16位，无空格）
- 网络连接是否正常
- 两步验证是否已启用

## 替代方案

如果Gmail配置复杂，也可以使用其他邮件服务：

### 163邮箱 SMTP
```python
self.smtp_server = "smtp.163.com"
self.smtp_port = 587
```

### QQ邮箱 SMTP
```python
self.smtp_server = "smtp.qq.com"
self.smtp_port = 587
```

### Outlook邮箱 SMTP
```python
self.smtp_server = "smtp-mail.outlook.com"
self.smtp_port = 587
```
```

你可以按照以下步骤配置Gmail邮件发送：

## 🛠️ **Gmail配置步骤：**

1. **启用Gmail两步验证** 