from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import sqlite3
import os
import pandas as pd
from io import BytesIO
import json
from datetime import datetime

app = Flask(__name__)
CORS(app)  # 允许前端跨域访问

# 数据库文件路径
DATABASE = 'contacts.db'

def init_db():
    """初始化数据库（新结构）"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # 创建联系人表（去掉单独的phone和email字段）
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS contacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            is_favorite BOOLEAN DEFAULT 0,
            created_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 创建联系方式表（支持多个联系方式）
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS contact_methods (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            contact_id INTEGER NOT NULL,
            method_type TEXT NOT NULL,  -- phone, email, address, social, etc.
            method_value TEXT NOT NULL,
            FOREIGN KEY (contact_id) REFERENCES contacts(id) ON DELETE CASCADE
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ 数据库初始化完成（新结构）")

@app.route('/')
def hello():
    return jsonify({
        "message": "通讯录后端API运行成功！",
        "version": "2.0",
        "features": ["书签功能", "多个联系方式", "导入导出"]
    })

@app.route('/health')
def health_check():
    return jsonify({"status": "healthy", "message": "服务运行正常"}), 200

# ========== 联系人管理 ==========

@app.route('/contacts', methods=['GET'])
def get_contacts():
    """获取所有联系人及其联系方式"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # 获取所有联系人
    cursor.execute('SELECT id, name, is_favorite, created_time FROM contacts ORDER BY is_favorite DESC, created_time DESC')
    contacts = cursor.fetchall()
    
    # 获取所有联系方式
    cursor.execute('SELECT contact_id, method_type, method_value FROM contact_methods ORDER BY contact_id, method_type')
    methods = cursor.fetchall()
    
    conn.close()
    
    # 组装数据
    contact_list = []
    for contact in contacts:
        contact_id, name, is_favorite, created_time = contact
        
        # 查找该联系人的所有联系方式
        contact_methods = []
        for method in methods:
            if method[0] == contact_id:
                contact_methods.append({
                    'type': method[1],
                    'value': method[2]
                })
        
        contact_list.append({
            'id': contact_id,
            'name': name,
            'is_favorite': bool(is_favorite),
            'created_time': created_time,
            'methods': contact_methods
        })
    
    return jsonify(contact_list)

@app.route('/contacts', methods=['POST'])
def add_contact():
    """添加新联系人（带多个联系方式）"""
    data = request.json
    name = data.get('name')
    methods = data.get('methods', [])  # 格式: [{"type": "phone", "value": "13800138000"}, ...]
    
    if not name:
        return jsonify({"error": "姓名不能为空"}), 400
    
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    try:
        # 插入联系人
        cursor.execute('INSERT INTO contacts (name) VALUES (?)', (name,))
        contact_id = cursor.lastrowid
        
        # 插入所有联系方式
        for method in methods:
            method_type = method.get('type')
            method_value = method.get('value')
            if method_type and method_value:
                cursor.execute(
                    'INSERT INTO contact_methods (contact_id, method_type, method_value) VALUES (?, ?, ?)',
                    (contact_id, method_type, method_value)
                )
        
        conn.commit()
        return jsonify({
            "message": "联系人添加成功",
            "id": contact_id,
            "name": name
        }), 201
        
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

@app.route('/contacts/<int:contact_id>', methods=['PUT'])
def update_contact(contact_id):
    """更新联系人（包括联系方式）"""
    data = request.json
    name = data.get('name')
    methods = data.get('methods', [])
    
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    try:
        # 更新联系人基本信息
        if name:
            cursor.execute('UPDATE contacts SET name=? WHERE id=?', (name, contact_id))
        
        # 删除旧的联系方式
        cursor.execute('DELETE FROM contact_methods WHERE contact_id=?', (contact_id,))
        
        # 插入新的联系方式
        for method in methods:
            method_type = method.get('type')
            method_value = method.get('value')
            if method_type and method_value:
                cursor.execute(
                    'INSERT INTO contact_methods (contact_id, method_type, method_value) VALUES (?, ?, ?)',
                    (contact_id, method_type, method_value)
                )
        
        conn.commit()
        return jsonify({"message": "联系人更新成功"})
        
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

@app.route('/contacts/<int:contact_id>', methods=['DELETE'])
def delete_contact(contact_id):
    """删除联系人（级联删除联系方式）"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    try:
        cursor.execute('DELETE FROM contacts WHERE id=?', (contact_id,))
        conn.commit()
        affected_rows = cursor.rowcount
        
        if affected_rows > 0:
            return jsonify({"message": "联系人删除成功"})
        else:
            return jsonify({"error": "联系人不存在"}), 404
            
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

# ========== 书签功能 ==========

@app.route('/contacts/<int:contact_id>/favorite', methods=['PUT'])
def toggle_favorite(contact_id):
    """切换联系人的收藏状态"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    try:
        cursor.execute('UPDATE contacts SET is_favorite = NOT is_favorite WHERE id=?', (contact_id,))
        conn.commit()
        
        # 获取更新后的状态
        cursor.execute('SELECT name, is_favorite FROM contacts WHERE id=?', (contact_id,))
        result = cursor.fetchone()
        
        if result:
            return jsonify({
                "message": f"{'取消' if result[1] else '添加'}收藏成功",
                "name": result[0],
                "is_favorite": bool(result[1])
            })
        else:
            return jsonify({"error": "联系人不存在"}), 404
            
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

@app.route('/contacts/favorites', methods=['GET'])
def get_favorites():
    """获取所有收藏的联系人"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT c.id, c.name, c.is_favorite, c.created_time,
               cm.method_type, cm.method_value
        FROM contacts c
        LEFT JOIN contact_methods cm ON c.id = cm.contact_id
        WHERE c.is_favorite = 1
        ORDER BY c.created_time DESC
    ''')
    
    results = cursor.fetchall()
    conn.close()
    
    # 组织数据
    favorites = {}
    for row in results:
        contact_id = row[0]
        if contact_id not in favorites:
            favorites[contact_id] = {
                'id': contact_id,
                'name': row[1],
                'is_favorite': bool(row[2]),
                'created_time': row[3],
                'methods': []
            }
        
        if row[4] and row[5]:  # 如果有联系方式
            favorites[contact_id]['methods'].append({
                'type': row[4],
                'value': row[5]
            })
    
    return jsonify(list(favorites.values()))

# ========== 导入导出功能 ==========

@app.route('/contacts/export', methods=['GET'])
def export_contacts():
    """导出所有联系人到Excel"""
    try:
        conn = sqlite3.connect(DATABASE)
        
        # 查询所有联系人及其联系方式
        query = '''
            SELECT 
                c.id,
                c.name,
                c.is_favorite,
                GROUP_CONCAT(
                    CASE 
                        WHEN cm.method_type = 'phone' THEN cm.method_value
                        ELSE NULL
                    END
                ) as phones,
                GROUP_CONCAT(
                    CASE 
                        WHEN cm.method_type = 'email' THEN cm.method_value
                        ELSE NULL
                    END
                ) as emails,
                GROUP_CONCAT(
                    CASE 
                        WHEN cm.method_type NOT IN ('phone', 'email') 
                        THEN cm.method_type || ': ' || cm.method_value
                        ELSE NULL
                    END
                ) as other_methods
            FROM contacts c
            LEFT JOIN contact_methods cm ON c.id = cm.contact_id
            GROUP BY c.id
        '''
        
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        # 清理数据
        if 'phones' in df.columns:
            df['phones'] = df['phones'].apply(lambda x: x.replace(',', ';') if pd.notna(x) else '')
        if 'emails' in df.columns:
            df['emails'] = df['emails'].apply(lambda x: x.replace(',', ';') if pd.notna(x) else '')
        
        # 创建Excel文件
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='通讯录', index=False)
            
            # 获取工作表并设置列宽
            worksheet = writer.sheets['通讯录']
            worksheet.column_dimensions['A'].width = 8   # ID
            worksheet.column_dimensions['B'].width = 15  # 姓名
            worksheet.column_dimensions['C'].width = 10  # 收藏
            worksheet.column_dimensions['D'].width = 25  # 电话
            worksheet.column_dimensions['E'].width = 30  # 邮箱
            worksheet.column_dimensions['F'].width = 35  # 其他
        
        output.seek(0)
        
        # 生成文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f'通讯录_导出_{timestamp}.xlsx'
        
        return send_file(
            output,
            download_name=filename,
            as_attachment=True,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
    except Exception as e:
        return jsonify({"error": f"导出失败: {str(e)}"}), 500

@app.route('/contacts/import', methods=['POST'])
def import_contacts():
    """从Excel导入联系人"""
    try:
        if 'file' not in request.files:
            return jsonify({"error": "没有上传文件"}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({"error": "没有选择文件"}), 400
        
        # 检查文件格式
        if not (file.filename.endswith('.xlsx') or file.filename.endswith('.xls')):
            return jsonify({"error": "只支持Excel文件 (.xlsx, .xls)"}), 400
        
        # 读取Excel文件
        df = pd.read_excel(file)
        
        # 检查必要的列
        required_columns = ['name']
        for col in required_columns:
            if col not in df.columns:
                return jsonify({"error": f"Excel缺少必要列: {col}"}), 400
        
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        success_count = 0
        error_count = 0
        errors = []
        
        for index, row in df.iterrows():
            try:
                # 插入联系人
                name = str(row['name']).strip()
                if not name:
                    continue
                
                is_favorite = int(row.get('is_favorite', 0)) if pd.notna(row.get('is_favorite')) else 0
                
                cursor.execute(
                    'INSERT INTO contacts (name, is_favorite) VALUES (?, ?)',
                    (name, is_favorite)
                )
                contact_id = cursor.lastrowid
                
                # 处理电话
                if 'phones' in df.columns and pd.notna(row.get('phones')):
                    phones = str(row['phones']).split(';')
                    for phone in phones:
                        phone = phone.strip()
                        if phone:
                            cursor.execute(
                                'INSERT INTO contact_methods (contact_id, method_type, method_value) VALUES (?, ?, ?)',
                                (contact_id, 'phone', phone)
                            )
                
                # 处理邮箱
                if 'emails' in df.columns and pd.notna(row.get('emails')):
                    emails = str(row['emails']).split(';')
                    for email in emails:
                        email = email.strip()
                        if email:
                            cursor.execute(
                                'INSERT INTO contact_methods (contact_id, method_type, method_value) VALUES (?, ?, ?)',
                                (contact_id, 'email', email)
                            )
                
                success_count += 1
                
            except Exception as e:
                error_count += 1
                errors.append(f"第{index+2}行错误: {str(e)}")
        
        conn.commit()
        conn.close()
        
        return jsonify({
            "message": f"导入完成！成功: {success_count}条，失败: {error_count}条",
            "success_count": success_count,
            "error_count": error_count,
            "errors": errors if errors else None
        })
        
    except Exception as e:
        return jsonify({"error": f"导入失败: {str(e)}"}), 500

# ========== 辅助功能 ==========

@app.route('/contacts/search/<keyword>', methods=['GET'])
def search_contacts(keyword):
    """搜索联系人（按姓名或联系方式）"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # 搜索联系人
    cursor.execute('''
        SELECT DISTINCT c.id, c.name, c.is_favorite, c.created_time
        FROM contacts c
        LEFT JOIN contact_methods cm ON c.id = cm.contact_id
        WHERE c.name LIKE ? OR cm.method_value LIKE ?
        ORDER BY c.is_favorite DESC, c.created_time DESC
    ''', (f'%{keyword}%', f'%{keyword}%'))
    
    contacts = cursor.fetchall()
    
    # 获取这些联系人的所有联系方式
    contact_ids = [str(c[0]) for c in contacts]
    if contact_ids:
        placeholders = ','.join(['?'] * len(contact_ids))
        cursor.execute(f'''
            SELECT contact_id, method_type, method_value 
            FROM contact_methods 
            WHERE contact_id IN ({placeholders})
        ''', contact_ids)
        methods = cursor.fetchall()
    else:
        methods = []
    
    conn.close()
    
    # 组装数据
    contact_list = []
    for contact in contacts:
        contact_id = contact[0]
        contact_methods = []
        
        for method in methods:
            if method[0] == contact_id:
                contact_methods.append({
                    'type': method[1],
                    'value': method[2]
                })
        
        contact_list.append({
            'id': contact_id,
            'name': contact[1],
            'is_favorite': bool(contact[2]),
            'created_time': contact[3],
            'methods': contact_methods
        })
    
    return jsonify(contact_list)

@app.route('/contacts/stats', methods=['GET'])
def get_stats():
    """获取统计数据"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) FROM contacts')
    total = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM contacts WHERE is_favorite = 1')
    favorites = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(DISTINCT contact_id) FROM contact_methods WHERE method_type = "phone"')
    with_phone = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(DISTINCT contact_id) FROM contact_methods WHERE method_type = "email"')
    with_email = cursor.fetchone()[0]
    
    conn.close()
    
    return jsonify({
        "total_contacts": total,
        "favorite_contacts": favorites,
        "contacts_with_phone": with_phone,
        "contacts_with_email": with_email
    })

# ========== 启动应用 ==========

if __name__ == '__main__':
    # 初始化数据库
    init_db()
    
    port = int(os.environ.get("PORT", 5000))
    print("=" * 50)
    print("📱 通讯录管理系统后端")
    print(f"🚀 API地址: http://0.0.0.0:{port}")
    print("✅ 支持功能: 书签、多联系方式、导入导出")
    print("=" * 50)
    
    app.run(host='0.0.0.0', port=port, debug=False)