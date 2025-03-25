import base64
import imaplib
import email
import json
import re
from datetime import datetime
from email.header import decode_header
from django.http import request
from blog.functions.utils import gpt_api
from blog.models import EmailAccount


def connect_to_email(username, password, imap_url="imap.qq.com"):
    imap_server = imaplib.IMAP4_SSL(imap_url)
    imap_server.login(username, password)
    return imap_server


def get_recent_email_ids(imap_server, contact_email='', subject_keyword='', n=1, folder="INBOX"):
    imap_server.select(folder)
    # 指定联系人查找
    # status, data = imap_server.search(None, f'FROM "cyuhan186@gmail.com"')
    # status, data = imap_server.search('UTF-8', f'(FROM "{contact_email}" SUBJECT "{subject_keyword}")')

    # 对中文 subject_keyword 进行 Base64 编码
    encoded_subject = base64.b64encode(subject_keyword.encode('utf-8')).decode('ascii')
    # 拼接编码后的搜索条件
    subject_search = f'SUBJECT "=?UTF-8?B?{encoded_subject}?="'
    status, data = imap_server.search('UTF-8', f'FROM "{contact_email}"', subject_search)
    email_ids = data[0].split()
    # print(email_ids)
    return email_ids[-n:]


def decode_email_header(header):
    decoded_header = decode_header(header)
    header_bytes, encoding = decoded_header[0]
    return header_bytes.decode(encoding if encoding else "utf-8") if isinstance(header_bytes, bytes) else header_bytes


def split_body(text):
    # Find the position of "On" in the text
    position = text.find("On")

    # Split text into two parts based on the position of "On"
    if position != -1:
        before_on = text[:position]
        after_on = text[position:]
    else:
        before_on = ''
        after_on = ''  # If "On" is not found, the after part is empty
    # print(before_on, after_on)
    return before_on, after_on

def extract_email_content(msg):
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition"))
            if "attachment" not in content_disposition:
                if content_type == "text/plain" or content_type == "text/html":
                    return part.get_payload(decode=True).decode(part.get_content_charset("utf-8"))
    else:
        return msg.get_payload(decode=True).decode(msg.get_content_charset("utf-8"))
    return ""

def clean_text(text):
    """去除HTML标签、特殊字符，并提取纯文本内容"""
    text = re.sub(r'<.*?>', '', text)  # 去除HTML标签
    text = re.sub(r'\s+', ' ', text).strip()  # 去除多余空格
    return text

# 只支持存存文字 fetch
def fetch_related_emails(imap_server, email_ids,timeout=60):
    related_emails = []
    # 设置 IMAP 超时
    imap_server.timeout = timeout
    for email_id in reversed(email_ids):
        status, data = imap_server.fetch(email_id, "(RFC822)")
        email_message = email.message_from_bytes(data[0][1])

        subject, encoding = decode_header(email_message["Subject"])[0]
        if isinstance(subject, bytes):
            subject = subject.decode(encoding or "utf-8")

        date = email_message["Date"]

        prompt = (
            "帮我总结一下邮件，去除邮件中的复杂/无用信息，返回Str形式。\n"
            "你需要总结邮件的Body（只包含单邮件内容）以及Other（只包含双方的历史对话，可能为空）。\n"
            
            f"我的邮件内容: {email_message}"
            
            "请只按照以下格式返回（JSON格式）方便我放到json.loads里面：\n"
            '{"Body": "xxx", "Other": "xxx"}\n'
        )

        def clean_response(response):
            # 去除首尾空白字符
            cleaned = response.strip()
            # 如果存在BOM字符，则去除
            cleaned = cleaned.lstrip('\ufeff')
            # 去除 Markdown 代码块标记，如 ``` 或 ```json
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.MULTILINE)
            cleaned = re.sub(r"\s*```$", "", cleaned, flags=re.MULTILINE)
            return cleaned.strip()

        response = clean_response(gpt_api(prompt))

        # 尝试直接解析JSON
        try:
            data = json.loads(response)
            body = data.get("Body", "")
            other = data.get("Other", "")
        except Exception as e:
            print("JSON解析错误：", e)
            body, other = None, None
        # print("Body:", body)
        # print("Other:", other)
        related_emails.append({"Subject": subject, "Date": date, "Body": body, "Other": other})

    return related_emails

def split_conversations_and_store(emails, username):
    dialogue_dict = {}
    for email_info in emails:
        body = email_info["Body"]
        conversations = body.split("> Original")

    return dialogue_dict

def get_relate_emails(user_email, password, contact_email, subject_keyword):
    # Connect the the user mail server
    imap_server = connect_to_email(user_email, password)
    related_email_infor = []
    try:
        related_ids = get_recent_email_ids(imap_server, contact_email, subject_keyword, n=1, folder="INBOX")
        related_email_infor = fetch_related_emails(imap_server, related_ids)
    except Exception as e:
        print('Failed to fetch related emails')
    finally:
        return related_email_infor


def summary_infor(email_data, user_id):
    # 从数据库获取当前用户的 email 信息
    email_acc = EmailAccount.objects.get(user_id=user_id)
    user_email = email_acc.email

    # 获取信息
    fetch_emails = email_data.get('email_data')
    receiver_email = email_data.get('receiver_email', 'No provide')
    subject = email_data.get('subject', '用户未提供 请自己生成')
    language = email_data.get('language', 'No provide')
    style = email_data.get('style', 'No provide')
    purpose = email_data.get('purpose', 'No provide')
    sender_role = email_data.get('senderRole', 'No provide')
    receiver_role = email_data.get('receiverRole', 'No provide')
    additional_req = email_data.get('additionalReq', 'No provide')

    gpt_history = ''
    model = '撰写'

    if fetch_emails:
        email_info = fetch_emails[0]
        raw_body_history = email_info['Body'] + email_info['Other']
        model = '回复'

        # 格式化旧邮件历史
        send_message = (
            f"帮我整理一下fetch收件箱 一份邮件的body，我作为用户1: {user_email}, 将发送邮件给用户2: {receiver_email}. "
            "固定只输入以下格式:\n"
            "**对话1: 用户1: 问题 ; 用户2: 回答**\n"
            "**对话2: 用户1: 问题 ; 用户2: 回答**\n"
            "...\n"
            f"**最后的对话n: 用户1: 问题 ; 用户2: {email_info['Body']}**\n\n"
            "（注意: 1. 根据时间升序 2. 没有因果关系不要放在一个对话!! 另起一个对话，空的内容为 None）\n"
            f"以下是邮件的 content： {raw_body_history}"
        )

        gpt_history = gpt_api(send_message)

    # 创建邮件提示
    email_prompt = (
        f"{model} 一封主题为: {subject} 的邮件,语言为 {language}。"
        f"邮件目的：{purpose} 风格为: {style}\n"
        "**收件人信息：**\n"
        f"姓名/职位: {receiver_role}\n"
        f"邮箱地址: {receiver_email}\n"
        "**发件人信息：**\n"
        f"姓名/职位: {sender_role}\n"
        f"邮箱地址: {user_email}\n"
        f"**其他要求: {additional_req}**\n"
    )
    if fetch_emails:
        email_prompt += (
            "**注意只需要返回正文 Content, 不需要包含 Subject！"
            "邮件历史内容可能提供（按时间升序，最后一个对话为最新的），只供理解，不要重复加在内容中（user1 为自己，user2 为对方）:**\n"
            f"{gpt_history}\n\n")

    # print(email_prompt)
    return gpt_api(email_prompt)

# def main():
#     user_email = "1208481203@qq.com"
#     password = "reltwsrnlvjrfeee"
#     target_address = "cyuhan186@gmail.com"
#
#     imap_server = connect_to_email(user_email, password)
#     try:
#         recent_email_ids = get_recent_email_ids(imap_server, 1)
#         related_emails = fetch_related_emails(imap_server, target_address, recent_email_ids)
#         # Version1:only for single mail (may contains reply)
#         summary_infor(related_emails,user_email)
#
#     finally:
#         imap_server.logout()


# if __name__ == "__main__":
#     main()