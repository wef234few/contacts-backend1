#!/usr/bin/env python3
"""
通讯录系统完整API测试脚本
测试所有功能：书签、多联系方式、导入导出
"""

import requests
import json
import os
import time
import pandas as pd
from io import BytesIO
import sys

# API基础地址 - 根据实际情况修改
BASE_URL = "http://localhost:5000"  # 本地测试
# BASE_URL = "https://你的项目名.railway.app"  # Railway部署

def print_section(title):
    """打印章节标题"""
    print("\n" + "=" * 60)
    print(f"🧪 {title}")
    print("=" * 60)

def test_health():
    """测试健康检查"""
    print_section("1. 健康检查测试")
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=10)
        print(f"✅ 状态码: {response.status_code}")
        print(f"✅ 响应内容: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ 健康检查失败: {e}")
        return False

def test_add_contact():
    """测试添加联系人（带多个联系方式）"""
    print_section("2. 添加联系人测试")
    
    test_contact = {
        "name": "测试用户张三",
        "methods": [
            {"type": "phone", "value": "13800138000"},
            {"type": "phone", "value": "13800138001"},
            {"type": "email", "value": "zhangsan@example.com"},
            {"type": "address", "value": "北京市海淀区"},
            {"type": "social", "value": "@zhangsan"}
        ]
    }
    
    try:
        response = requests.post(f"{BASE_URL}/contacts", 
                               json=test_contact,
                               headers={"Content-Type": "application/json"})
        
        print(f"✅ 状态码: {response.status_code}")
        result = response.json()
        print(f"✅ 响应内容: {result}")
        
        if response.status_code == 201:
            print("✅ 联系人添加成功")
            return result.get("id")
        else:
            print(f"❌ 联系人添加失败: {result.get('error', '未知错误')}")
            return None
            
    except Exception as e:
        print(f"❌ 添加联系人异常: {e}")
        return None

def test_get_contacts():
    """测试获取所有联系人"""
    print_section("3. 获取联系人列表测试")
    
    try:
        response = requests.get(f"{BASE_URL}/contacts", timeout=10)
        print(f"✅ 状态码: {response.status_code}")
        
        contacts = response.json()
        print(f"✅ 联系人数量: {len(contacts)}")
        
        if contacts:
            print("✅ 示例联系人信息:")
            for i, contact in enumerate(contacts[:2]):  # 只显示前2个
                print(f"    {i+1}. {contact.get('name')} (ID: {contact.get('id')})")
                print(f"       收藏: {'是' if contact.get('is_favorite') else '否'}")
                if contact.get('methods'):
                    print(f"       联系方式: {len(contact.get('methods'))} 个")
                    for method in contact.get('methods')[:3]:  # 显示前3个联系方式
                        print(f"         - {method.get('type')}: {method.get('value')}")
                print()
        
        return len(contacts) > 0
        
    except Exception as e:
        print(f"❌ 获取联系人失败: {e}")
        return False

def test_toggle_favorite():
    """测试切换收藏状态"""
    print_section("4. 书签功能测试")
    
    try:
        # 先获取一个联系人
        response = requests.get(f"{BASE_URL}/contacts")
        contacts = response.json()
        
        if not contacts:
            print("⚠️  没有联系人可以测试书签功能")
            return False
        
        contact_id = contacts[0]['id']
        contact_name = contacts[0]['name']
        
        print(f"✅ 测试联系人: {contact_name} (ID: {contact_id})")
        
        # 切换收藏状态
        response = requests.put(f"{BASE_URL}/contacts/{contact_id}/favorite")
        print(f"✅ 状态码: {response.status_code}")
        result = response.json()
        print(f"✅ 响应内容: {result}")
        
        # 验证状态是否改变
        response = requests.get(f"{BASE_URL}/contacts")
        updated_contact = next((c for c in response.json() if c['id'] == contact_id), None)
        
        if updated_contact:
            print(f"✅ 更新后收藏状态: {'已收藏' if updated_contact['is_favorite'] else '未收藏'}")
            return True
        else:
            print("❌ 无法验证收藏状态更新")
            return False
            
    except Exception as e:
        print(f"❌ 书签功能测试失败: {e}")
        return False

def test_update_contact():
    """测试更新联系人"""
    print_section("5. 更新联系人测试")
    
    try:
        # 先获取一个联系人
        response = requests.get(f"{BASE_URL}/contacts")
        contacts = response.json()
        
        if not contacts:
            print("⚠️  没有联系人可以测试更新功能")
            return False
        
        contact_id = contacts[0]['id']
        old_name = contacts[0]['name']
        
        print(f"✅ 测试联系人: {old_name} (ID: {contact_id})")
        
        # 更新联系人信息
        update_data = {
            "name": f"{old_name}_已更新",
            "methods": [
                {"type": "phone", "value": "13999999999"},
                {"type": "email", "value": "updated@example.com"}
            ]
        }
        
        response = requests.put(f"{BASE_URL}/contacts/{contact_id}", 
                              json=update_data,
                              headers={"Content-Type": "application/json"})
        
        print(f"✅ 状态码: {response.status_code}")
        result = response.json()
        print(f"✅ 响应内容: {result}")
        
        # 验证更新
        response = requests.get(f"{BASE_URL}/contacts")
        updated_contact = next((c for c in response.json() if c['id'] == contact_id), None)
        
        if updated_contact and updated_contact['name'] == update_data['name']:
            print(f"✅ 更新成功: {old_name} -> {updated_contact['name']}")
            print(f"✅ 联系方式数量: {len(updated_contact.get('methods', []))}")
            return True
        else:
            print("❌ 更新验证失败")
            return False
            
    except Exception as e:
        print(f"❌ 更新联系人测试失败: {e}")
        return False

def test_search_contacts():
    """测试搜索功能"""
    print_section("6. 搜索功能测试")
    
    try:
        # 搜索包含"张"的联系人
        keyword = "张"
        response = requests.get(f"{BASE_URL}/contacts/search/{keyword}")
        
        print(f"✅ 状态码: {response.status_code}")
        results = response.json()
        print(f"✅ 搜索结果数量: {len(results)}")
        
        if results:
            print("✅ 搜索结果:")
            for i, contact in enumerate(results[:3]):  # 显示前3个结果
                print(f"    {i+1}. {contact.get('name')} (ID: {contact.get('id')})")
        
        return response.status_code == 200
        
    except Exception as e:
        print(f"❌ 搜索功能测试失败: {e}")
        return False

def test_export_contacts():
    """测试导出功能"""
    print_section("7. 导出功能测试")
    
    try:
        response = requests.get(f"{BASE_URL}/contacts/export", timeout=30)
        print(f"✅ 状态码: {response.status_code}")
        
        if response.status_code == 200:
            # 保存导出的文件
            filename = "test_export.xlsx"
            with open(filename, 'wb') as f:
                f.write(response.content)
            
            file_size = os.path.getsize(filename)
            print(f"✅ 导出成功！文件大小: {file_size:,} 字节")
            print(f"✅ 文件已保存为: {filename}")
            
            # 用pandas读取验证文件
            try:
                df = pd.read_excel(filename)
                print(f"✅ Excel文件验证: {df.shape[0]} 行, {df.shape[1]} 列")
                print(f"✅ 列名: {list(df.columns)}")
                
                if df.shape[0] > 0:
                    print("✅ 前几条数据:")
                    print(df.head(3).to_string())
                    
                return True
            except Exception as e:
                print(f"⚠️  Excel文件读取失败: {e}")
                return False
        else:
            error_msg = response.json().get('error', '未知错误')
            print(f"❌ 导出失败: {error_msg}")
            return False
            
    except Exception as e:
        print(f"❌ 导出功能测试失败: {e}")
        return False

def test_import_contacts():
    """测试导入功能"""
    print_section("8. 导入功能测试")
    
    try:
        # 先创建一个测试Excel文件
        test_data = pd.DataFrame({
            'name': ['导入用户1', '导入用户2', '导入用户3'],
            'is_favorite': [1, 0, 1],
            'phones': ['13800138000;13800138001', '13900139000', '13700137000'],
            'emails': ['import1@example.com', 'import2@example.com', 'import3@example.com'],
            'other_methods': ['微信: user1', '地址: 上海', '微信: user3']
        })
        
        # 保存为Excel文件
        excel_file = "test_import.xlsx"
        test_data.to_excel(excel_file, index=False)
        print(f"✅ 创建测试Excel文件: {excel_file}")
        print(f"✅ 测试数据: {test_data.shape[0]} 行")
        
        # 发送导入请求
        with open(excel_file, 'rb') as f:
            files = {'file': (excel_file, f, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
            response = requests.post(f"{BASE_URL}/contacts/import", files=files, timeout=30)
        
        print(f"✅ 状态码: {response.status_code}")
        result = response.json()
        print(f"✅ 响应内容: {result}")
        
        if response.status_code == 200:
            print(f"✅ 导入结果: {result.get('message')}")
            
            # 验证导入的数据
            time.sleep(2)  # 等待数据写入
            
            # 搜索导入的联系人
            response = requests.get(f"{BASE_URL}/contacts/search/导入用户")
            imported_contacts = response.json()
            print(f"✅ 导入后包含'导入用户'的联系人数量: {len(imported_contacts)}")
            
            # 清理测试文件
            if os.path.exists(excel_file):
                os.remove(excel_file)
                print(f"✅ 已清理测试文件: {excel_file}")
            
            return result.get('success_count', 0) > 0
        else:
            print(f"❌ 导入失败: {result.get('error', '未知错误')}")
            return False
            
    except Exception as e:
        print(f"❌ 导入功能测试失败: {e}")
        return False

def test_stats():
    """测试统计信息"""
    print_section("9. 统计信息测试")
    
    try:
        response = requests.get(f"{BASE_URL}/contacts/stats")
        print(f"✅ 状态码: {response.status_code}")
        
        stats = response.json()
        print(f"✅ 统计信息:")
        print(f"   总联系人: {stats.get('total_contacts', 0)}")
        print(f"   收藏联系人: {stats.get('favorite_contacts', 0)}")
        print(f"   有电话的联系人: {stats.get('contacts_with_phone', 0)}")
        print(f"   有邮箱的联系人: {stats.get('contacts_with_email', 0)}")
        
        return response.status_code == 200
        
    except Exception as e:
        print(f"❌ 统计信息测试失败: {e}")
        return False

def test_delete_contact():
    """测试删除联系人"""
    print_section("10. 删除联系人测试")
    
    try:
        # 先获取一个联系人
        response = requests.get(f"{BASE_URL}/contacts")
        contacts = response.json()
        
        if not contacts:
            print("⚠️  没有联系人可以测试删除功能")
            return False
        
        # 选择最后一个联系人（避免删除重要数据）
        contact_to_delete = contacts[-1]
        contact_id = contact_to_delete['id']
        contact_name = contact_to_delete['name']
        
        print(f"✅ 测试删除联系人: {contact_name} (ID: {contact_id})")
        
        # 发送删除请求
        response = requests.delete(f"{BASE_URL}/contacts/{contact_id}")
        print(f"✅ 状态码: {response.status_code}")
        result = response.json()
        print(f"✅ 响应内容: {result}")
        
        # 验证是否删除成功
        time.sleep(1)
        response = requests.get(f"{BASE_URL}/contacts")
        remaining_contacts = response.json()
        
        # 检查联系人是否还在列表中
        deleted = True
        for contact in remaining_contacts:
            if contact['id'] == contact_id:
                deleted = False
                break
        
        if deleted:
            print("✅ 联系人删除成功验证")
            return True
        else:
            print("❌ 联系人删除验证失败")
            return False
            
    except Exception as e:
        print(f"❌ 删除联系人测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("\n" + "🌟" * 60)
    print("🚀 通讯录系统完整API测试")
    print("🌟" * 60)
    
    # 等待后端启动
    print("⏳ 等待后端服务启动...")
    time.sleep(3)
    
    test_results = []
    
    # 运行所有测试
    tests = [
        ("健康检查", test_health),
        ("添加联系人", test_add_contact),
        ("获取联系人", test_get_contacts),
        ("书签功能", test_toggle_favorite),
        ("更新联系人", test_update_contact),
        ("搜索功能", test_search_contacts),
        ("导出功能", test_export_contacts),
        ("导入功能", test_import_contacts),
        ("统计信息", test_stats),
        ("删除联系人", test_delete_contact)
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            print(f"\n▶️  开始测试: {test_name}")
            success = test_func()
            
            if success:
                print(f"✅ {test_name}: 通过")
                passed += 1
                test_results.append((test_name, "✅ 通过"))
            else:
                print(f"❌ {test_name}: 失败")
                failed += 1
                test_results.append((test_name, "❌ 失败"))
                
        except Exception as e:
            print(f"⚠️  {test_name}: 异常 - {e}")
            failed += 1
            test_results.append((test_name, f"⚠️  异常: {e}"))
    
    # 打印测试总结
    print("\n" + "📊" * 60)
    print("📈 测试结果总结")
    print("📊" * 60)
    
    for test_name, result in test_results:
        print(f"{test_name:20} {result}")
    
    print("\n" + "=" * 60)
    print(f"✅ 通过: {passed}")
    print(f"❌ 失败: {failed}")
    print(f"📊 总计: {passed + failed} 个测试")
    print(f"🏆 成功率: {passed/(passed+failed)*100:.1f}%")
    print("=" * 60)
    
    if failed == 0:
        print("\n🎉 恭喜！所有测试通过！")
        print("✅ 通讯录系统所有功能运行正常")
    else:
        print(f"\n⚠️  有 {failed} 个测试失败，请检查问题")
    
    # 清理测试文件
    cleanup_files = ["test_export.xlsx", "test_import.xlsx"]
    for file in cleanup_files:
        if os.path.exists(file):
            try:
                os.remove(file)
                print(f"🗑️  已清理: {file}")
            except:
                pass

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  测试被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 测试过程发生异常: {e}")
        sys.exit(1)