#!/usr/bin/env python3
"""
数据库迁移脚本 - 通讯录系统
将旧版本数据库迁移到新版本（支持书签、多联系方式）
"""

import sqlite3
import os
import shutil
from datetime import datetime

def migrate_database():
    """迁移数据库到新结构"""
    print("=" * 50)
    print("🔄 通讯录系统数据库迁移工具")
    print("=" * 50)
    
    old_db_path = 'contacts.db'
    
    # 检查旧数据库是否存在
    if not os.path.exists(old_db_path):
        print("❌ 未找到旧的数据库文件 contacts.db")
        print("✅ 将创建新的数据库结构...")
        create_new_database()
        return
    
    # 备份旧数据库
    backup_name = f"contacts_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    try:
        shutil.copy2(old_db_path, backup_name)
        print(f"📁 已备份旧数据库: {backup_name}")
    except Exception as e:
        print(f"❌ 备份数据库失败: {e}")
        return
    
    try:
        # 连接到旧数据库
        old_conn = sqlite3.connect(old_db_path)
        old_cursor = old_conn.cursor()
        
        # 检查旧表结构
        old_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='contacts'")
        if not old_cursor.fetchone():
            print("⚠️ 旧数据库中没有contacts表，将创建新结构")
            old_conn.close()
            create_new_database()
            return
        
        # 获取旧表结构
        old_cursor.execute("PRAGMA table_info(contacts)")
        old_columns = old_cursor.fetchall()
        
        print("📊 旧表结构分析:")
        column_names = []
        for col in old_columns:
            col_name = col[1]
            col_type = col[2]
            column_names.append(col_name)
            print(f"   - {col_name} ({col_type})")
        
        # 检查是否是新结构（已经有is_favorite字段）
        if 'is_favorite' in column_names:
            print("✅ 数据库已经是新结构，无需迁移")
            old_conn.close()
            return
        
        # 获取旧数据
        print("\n📥 正在读取旧数据...")
        old_cursor.execute('SELECT * FROM contacts')
        old_contacts = old_cursor.fetchall()
        
        # 根据列名创建映射
        name_index = column_names.index('name') if 'name' in column_names else None
        phone_index = column_names.index('phone') if 'phone' in column_names else None
        email_index = column_names.index('email') if 'email' in column_names else None
        id_index = column_names.index('id') if 'id' in column_names else 0
        
        if name_index is None:
            print("❌ 旧表缺少必需的name字段")
            old_conn.close()
            return
        
        print(f"✅ 找到 {len(old_contacts)} 个联系人")
        old_conn.close()
        
        # 创建新数据库
        print("\n🏗️ 创建新数据库结构...")
        new_conn = sqlite3.connect('contacts.db')
        new_cursor = new_conn.cursor()
        
        # 创建新表结构
        new_cursor.execute('''
            CREATE TABLE IF NOT EXISTS contacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                is_favorite BOOLEAN DEFAULT 0,
                created_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        new_cursor.execute('''
            CREATE TABLE IF NOT EXISTS contact_methods (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                contact_id INTEGER NOT NULL,
                method_type TEXT NOT NULL,
                method_value TEXT NOT NULL,
                FOREIGN KEY (contact_id) REFERENCES contacts(id) ON DELETE CASCADE
            )
        ''')
        
        # 迁移数据
        print("\n🚚 正在迁移数据...")
        migrated_count = 0
        error_count = 0
        
        for old_contact in old_contacts:
            try:
                # 提取数据
                contact_id = old_contact[id_index] if len(old_contact) > id_index else None
                name = old_contact[name_index] if len(old_contact) > name_index else ""
                
                # 插入新联系人表（不指定id，让SQLite自动生成）
                new_cursor.execute('INSERT INTO contacts (name) VALUES (?)', (name,))
                new_contact_id = new_cursor.lastrowid
                
                # 迁移电话
                if phone_index is not None and len(old_contact) > phone_index:
                    phone = old_contact[phone_index]
                    if phone and str(phone).strip():
                        new_cursor.execute(
                            'INSERT INTO contact_methods (contact_id, method_type, method_value) VALUES (?, ?, ?)',
                            (new_contact_id, 'phone', str(phone).strip())
                        )
                
                # 迁移邮箱
                if email_index is not None and len(old_contact) > email_index:
                    email = old_contact[email_index]
                    if email and str(email).strip():
                        new_cursor.execute(
                            'INSERT INTO contact_methods (contact_id, method_type, method_value) VALUES (?, ?, ?)',
                            (new_contact_id, 'email', str(email).strip())
                        )
                
                migrated_count += 1
                
                # 显示进度
                if migrated_count % 10 == 0:
                    print(f"  已迁移 {migrated_count} 个联系人...")
                    
            except Exception as e:
                error_count += 1
                print(f"  ⚠️ 迁移联系人失败 (ID: {contact_id}): {e}")
        
        new_conn.commit()
        new_conn.close()
        
        print("\n" + "=" * 50)
        print("📈 迁移完成！")
        print(f"✅ 成功迁移: {migrated_count} 个联系人")
        if error_count > 0:
            print(f"⚠️  迁移失败: {error_count} 个联系人")
        print(f"📁 旧数据库备份: {backup_name}")
        print("📊 新数据库结构:")
        print("  - contacts表: id, name, is_favorite, created_time")
        print("  - contact_methods表: id, contact_id, method_type, method_value")
        print("=" * 50)
        
    except Exception as e:
        print(f"\n❌ 迁移过程出错: {e}")
        print("⚠️  正在恢复备份...")
        try:
            if os.path.exists(backup_name):
                shutil.copy2(backup_name, old_db_path)
                print("✅ 已恢复原始数据库")
        except Exception as restore_error:
            print(f"❌ 恢复备份失败: {restore_error}")

def create_new_database():
    """创建全新的数据库结构"""
    try:
        # 删除可能存在的旧文件
        if os.path.exists('contacts.db'):
            os.remove('contacts.db')
            print("🗑️  已删除旧的数据库文件")
        
        # 创建新数据库
        conn = sqlite3.connect('contacts.db')
        cursor = conn.cursor()
        
        # 创建新表结构
        cursor.execute('''
            CREATE TABLE contacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                is_favorite BOOLEAN DEFAULT 0,
                created_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE contact_methods (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                contact_id INTEGER NOT NULL,
                method_type TEXT NOT NULL,
                method_value TEXT NOT NULL,
                FOREIGN KEY (contact_id) REFERENCES contacts(id) ON DELETE CASCADE
            )
        ''')
        
        # 添加一些示例数据（可选）
        add_sample_data = input("\n是否添加示例数据？(y/n): ").lower().strip()
        if add_sample_data == 'y' or add_sample_data == 'yes':
            print("\n📝 添加示例数据...")
            
            # 示例联系人1
            cursor.execute('INSERT INTO contacts (name, is_favorite) VALUES (?, ?)', 
                         ("张三", 1))
            contact1_id = cursor.lastrowid
            cursor.execute('INSERT INTO contact_methods (contact_id, method_type, method_value) VALUES (?, ?, ?)',
                         (contact1_id, 'phone', '13800138000'))
            cursor.execute('INSERT INTO contact_methods (contact_id, method_type, method_value) VALUES (?, ?, ?)',
                         (contact1_id, 'email', 'zhangsan@example.com'))
            
            # 示例联系人2
            cursor.execute('INSERT INTO contacts (name, is_favorite) VALUES (?, ?)', 
                         ("李四", 0))
            contact2_id = cursor.lastrowid
            cursor.execute('INSERT INTO contact_methods (contact_id, method_type, method_value) VALUES (?, ?, ?)',
                         (contact2_id, 'phone', '13900139000'))
            cursor.execute('INSERT INTO contact_methods (contact_id, method_type, method_value) VALUES (?, ?, ?)',
                         (contact2_id, 'phone', '13900139001'))
            cursor.execute('INSERT INTO contact_methods (contact_id, method_type, method_value) VALUES (?, ?, ?)',
                         (contact2_id, 'email', 'lisi@example.com'))
            
            # 示例联系人3
            cursor.execute('INSERT INTO contacts (name, is_favorite) VALUES (?, ?)', 
                         ("王五", 1))
            contact3_id = cursor.lastrowid
            cursor.execute('INSERT INTO contact_methods (contact_id, method_type, method_value) VALUES (?, ?, ?)',
                         (contact3_id, 'phone', '13700137000'))
            cursor.execute('INSERT INTO contact_methods (contact_id, method_type, method_value) VALUES (?, ?, ?)',
                         (contact3_id, 'address', '北京市海淀区'))
            
            print("✅ 添加了3个示例联系人")
        
        conn.commit()
        conn.close()
        
        print("\n" + "=" * 50)
        print("✅ 新数据库创建完成！")
        print("📊 数据库结构:")
        print("  - contacts表: id, name, is_favorite, created_time")
        print("  - contact_methods表: id, contact_id, method_type, method_value")
        print("=" * 50)
        
    except Exception as e:
        print(f"❌ 创建新数据库失败: {e}")

def verify_database():
    """验证数据库结构"""
    print("\n🔍 验证数据库结构...")
    
    if not os.path.exists('contacts.db'):
        print("❌ 数据库文件不存在")
        return False
    
    try:
        conn = sqlite3.connect('contacts.db')
        cursor = conn.cursor()
        
        # 检查表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        table_names = [table[0] for table in tables]
        
        print("📋 数据库中的表:")
        for table in table_names:
            print(f"  - {table}")
        
        # 检查contacts表结构
        if 'contacts' in table_names:
            cursor.execute("PRAGMA table_info(contacts)")
            columns = cursor.fetchall()
            print("\n📊 contacts表结构:")
            required_columns = ['id', 'name', 'is_favorite', 'created_time']
            for col in columns:
                col_name = col[1]
                col_type = col[2]
                status = "✅" if col_name in required_columns else "❌"
                print(f"  {status} {col_name} ({col_type})")
        
        # 检查contact_methods表结构
        if 'contact_methods' in table_names:
            cursor.execute("PRAGMA table_info(contact_methods)")
            columns = cursor.fetchall()
            print("\n📊 contact_methods表结构:")
            required_columns = ['id', 'contact_id', 'method_type', 'method_value']
            for col in columns:
                col_name = col[1]
                col_type = col[2]
                status = "✅" if col_name in required_columns else "❌"
                print(f"  {status} {col_name} ({col_type})")
        
        # 检查数据
        print("\n📈 数据统计:")
        cursor.execute("SELECT COUNT(*) FROM contacts")
        contact_count = cursor.fetchone()[0]
        print(f"  - 联系人数量: {contact_count}")
        
        cursor.execute("SELECT COUNT(*) FROM contact_methods")
        method_count = cursor.fetchone()[0]
        print(f"  - 联系方式数量: {method_count}")
        
        cursor.execute("SELECT COUNT(*) FROM contacts WHERE is_favorite = 1")
        favorite_count = cursor.fetchone()[0]
        print(f"  - 收藏联系人数量: {favorite_count}")
        
        conn.close()
        
        print("\n✅ 数据库验证完成")
        return True
        
    except Exception as e:
        print(f"❌ 验证数据库时出错: {e}")
        return False

if __name__ == '__main__':
    print("通讯录系统数据库迁移工具")
    print("1. 迁移现有数据库")
    print("2. 创建全新数据库")
    print("3. 验证数据库结构")
    
    choice = input("\n请选择操作 (1/2/3): ").strip()
    
    if choice == '1':
        migrate_database()
    elif choice == '2':
        create_new_database()
    elif choice == '3':
        verify_database()
    else:
        print("❌ 无效选择")
    
    input("\n按回车键退出...")