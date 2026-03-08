import os
import re

def process_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    original_content = content

    # Simple replaces in models, schemas, repos, tests
    # We replace "email" with "nick_id" in specific contexts
    content = content.replace('user.email', 'user.nick_id')
    content = content.replace('User.email', 'User.nick_id')
    content = content.replace('email=form.get("email")', 'nick_id=form.get("nick_id")')
    content = content.replace('.email', '.nick_id')
    
    # We need to be careful with template variables, e.g. {{ username }} etc.
    if 'get_user_by_email' in content:
        content = content.replace('get_user_by_email', 'get_user_by_nick_id')
        
    if 'EmailStr' in content:
        content = content.replace('EmailStr', 'str')
        content = content.replace('.str._validate', '') # cleanup if needed
        content = re.sub(r'from pydantic import .*EmailStr.*', '', content)
        
    if 'class UserCreate' in filepath or 'schemas/user.py' in filepath:
        content = content.replace('email: Optional[str] = None', 'nick_id: str')
        content = content.replace('email:', 'nick_id:')
        content = re.sub(r'@field_validator\("email"\)[\s\S]*?return email', '', content)
        
    if 'db/models/user.py' in filepath:
        content = content.replace('email = Column', 'nick_id = Column')

    if content != original_content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Updated {filepath}")

for root, dirs, files in os.walk('c:/Users/kmisiarz/projects/cash_game_tracker/backend'):
    for file in files:
        if file.endswith('.py') or file.endswith('.html'):
            process_file(os.path.join(root, file))
