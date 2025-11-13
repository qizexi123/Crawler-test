"""
通过公司找股东：巨潮：可以爬取
"""
"""
python版本: python>=3.10
# 安装依赖
pip install playwright

# linux 系统：
# 安装chromium
playwright install chromium

# 也可以一次安装所有浏览器驱动
playwright install
"""
import asyncio
import json
import csv
import random
import time

import aiofiles
import aiohttp
from playwright.async_api import async_playwright
import re
from bs4 import BeautifulSoup


async def load_stock_codes():
    async with aiofiles.open("data/stock_codes_mini.txt", "r") as f:
        codes = []
        async for line in f:
            cs = line.split(",")
            codes += [str(c) for c in cs if c.strip()]
        return codes


async def load_cookies():
    async with aiofiles.open("cookies/18664892760.txt", "r") as f:
        cookies_str = await f.read()
        cookies = []
        # 设置cookies
        if cookies_str and cookies_str.strip():
            for cookie in cookies_str.strip().split('; '):
                if '=' in cookie:
                    name, value = cookie.split('=', 1)
                    cookies.append({
                        'name': name.strip(),
                        'value': value.strip(),
                        'domain': '.cninfo.com.cn',  # 修改为巨潮资讯网的域名
                        'path': '/'
                    })
        return cookies


def extract_executives_info(html_content):
    """从HTML中提取高管信息"""
    soup = BeautifulSoup(html_content, 'html.parser')
    executives = []

    # 查找高管表格
    table_wrapper = soup.find('div', class_='el-table__body-wrapper')
    if not table_wrapper:
        print("未找到高管表格")
        return executives

    # 查找所有行
    rows = table_wrapper.find_all('tr', class_='el-table__row')
    print(f"找到 {len(rows)} 行高管数据")

    for row in rows:
        cells = row.find_all('td')
        if len(cells) >= 5:  # 确保有足够的列
            try:
                # 提取各列数据
                name = cells[0].get_text(strip=True)
                position = cells[1].get_text(strip=True)
                education = cells[2].get_text(strip=True)
                salary = cells[3].get_text(strip=True)
                shares = cells[4].get_text(strip=True)

                executive = {
                    '姓名': name,
                    '职务': position,
                    '学历': education,
                    '年薪(万元)': salary,
                    '持股数(股)': shares
                }
                executives.append(executive)
                print(f"提取高管: {name} - {position}")
            except Exception as e:
                print(f"解析行数据时出错: {e}")
                continue

    return executives


async def save_executives_data(executives, search_keyword, format_type='all'):
    """保存高管数据为JSON和CSV格式"""
    base_filename = f'results/executives_{search_keyword}'

    if format_type in ['json', 'all']:
        # 保存为JSON
        json_filename = f'{base_filename}.json'
        async with aiofiles.open(json_filename, 'w', encoding='utf-8') as f:
            await f.write(json.dumps(executives, ensure_ascii=False, indent=2))
        print(f"高管数据已保存为JSON: {json_filename}")

    if format_type in ['csv', 'all']:
        # 保存为CSV
        csv_filename = f'{base_filename}.csv'
        if executives:
            fieldnames = executives[0].keys()
            with open(csv_filename, 'w', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(executives)
            print(f"高管数据已保存为CSV: {csv_filename}")


async def search_and_save_page(url: str, search_keyword: str, headless: bool = True) -> bool:
    async with async_playwright() as p:
        # 启动浏览器
        browser = await p.chromium.launch(headless=headless)  # 设置为True可在后台运行
        context = await browser.new_context()
        # 设置cookie
        cookies = await load_cookies()
        await context.add_cookies(cookies)
        # 打开新页面
        page = await context.new_page()

        try:
            # 导航到目标网站
            await page.goto(url)
            print("已打开首页")

            # 等待搜索框加载完成
            await page.wait_for_selector('.search-input input.el-input__inner', timeout=10000)
            print("搜索框已加载")

            # 在搜索框中输入关键词
            search_input = page.locator('.search-input input.el-input__inner')
            await search_input.fill(search_keyword)
            print(f"已输入搜索关键词: {search_keyword}")

            # 点击搜索按钮
            search_button = page.locator('.chaxun-btn')
            await search_button.click()
            print("已点击搜索按钮")

            # 等待搜索结果加载
            await page.wait_for_timeout(3000)

            # 监听新页面的打开
            async with context.expect_page() as new_page_info:
                # 点击"公司介绍"链接
                company_intro_link = page.locator('a:has-text("公司介绍")')
                await company_intro_link.click()
                print("已点击公司介绍，等待新页面打开...")

            # 获取新页面
            new_page = await new_page_info.value
            await new_page.wait_for_load_state()
            print("新页面已加载完成")

            # 关闭旧页面
            await page.close()

            # 将page指向新页面
            page = new_page

            # 等待公司介绍页面加载
            await page.wait_for_timeout(2000)

            # 点击"公司高管"菜单项
            exec_menu = page.locator('.el-menu-item:has-text("公司高管")')
            await exec_menu.click()
            print("已点击公司高管")

            # 等待公司高管页面完全加载
            await page.wait_for_timeout(3000)

            # 获取页面HTML并移除所有JavaScript
            html_content = await page.content()

            # 提取高管信息
            print("开始提取高管信息...")
            executives = extract_executives_info(html_content)
            print(f"成功提取 {len(executives)} 条高管信息")

            # 保存高管数据
            await save_executives_data(executives, search_keyword)

            # 移除所有script标签
            cleaned_html = re.sub(r'<script\b[^<]*(?:(?!</script>)<[^<]*)*</script>', '', html_content,
                                  flags=re.IGNORECASE)

            # 移除所有事件处理属性（onclick, onload等）
            event_attrs = ['onclick', 'ondblclick', 'onmousedown', 'onmouseup', 'onmouseover',
                           'onmousemove', 'onmouseout', 'onkeydown', 'onkeypress', 'onkeyup',
                           'onload', 'onunload', 'onchange', 'onsubmit', 'onreset', 'onselect',
                           'onblur', 'onfocus', 'onabort', 'onerror']

            for attr in event_attrs:
                cleaned_html = re.sub(f'{attr}="[^"]*"', '', cleaned_html, flags=re.IGNORECASE)
                cleaned_html = re.sub(f"{attr}='[^']*'", '', cleaned_html, flags=re.IGNORECASE)

            # 移除href中的javascript:链接
            cleaned_html = re.sub(r'href="javascript:[^"]*"', 'href="#"', cleaned_html, flags=re.IGNORECASE)
            cleaned_html = re.sub(r"href='javascript:[^']*'", "href='#'", cleaned_html, flags=re.IGNORECASE)

            # 禁用所有表单元素
            cleaned_html = cleaned_html.replace('<input ', '<input disabled ')
            cleaned_html = cleaned_html.replace('<button ', '<button disabled ')
            cleaned_html = cleaned_html.replace('<select ', '<select disabled ')
            cleaned_html = cleaned_html.replace('<textarea ', '<textarea disabled ')

            # 移除meta标签中的自动刷新
            cleaned_html = re.sub(r'<meta[^>]*http-equiv[^>]*refresh[^>]*>', '', cleaned_html, flags=re.IGNORECASE)

            # 保存清理后的HTML到文件
            filename = f'results/company_executives_page_{search_keyword}.html'
            async with aiofiles.open(filename, 'w', encoding='utf-8') as f:
                await f.write(cleaned_html)

            print(f"页面已成功保存为 {filename}")
            print("所有JavaScript和交互功能已被移除")
            print("-" * 50)

            return True
        except Exception as e:
            print(f"操作过程中出现错误: {e}")
            # 保存错误截图
            # await page.screenshot(path=f'temps/error_screenshot_{search_keyword}.png')
            # print(f"错误截图已保存为 temps/error_screenshot_{search_keyword}.png")
            return False

        finally:
            # 关闭浏览器
            await browser.close()


# 批量处理多个公司
async def batch_process_companies(url: str):
    t1 = time.time()

    # url = "https://www.cninfo.com.cn/new/index"
    # companies = ["000001", "000002", "000003", "000004", "000005", "000006", "600036"]  # 可以添加更多公司代码
    companies = await load_stock_codes()
    print(f"加载到公司数量：{len(companies)}: 前五：{companies[:5]}")

    success_count = 0
    error_count = 0
    for company in companies:
        print(f"开始处理公司: {company}")
        rs = await search_and_save_page(url, company)
        if rs:
            success_count += 1
        else:
            error_count += 1
        await asyncio.sleep(random.randint(3, 6))  # 添加延迟避免请求过快

    t2 = time.time()
    print("=" * 50)
    print()
    print()
    print(f"全部处理完成：{t2 - t1:.3f}s")
    print(f"总记录数：{len(companies)}, 成功数量: {success_count}, 失败数量: {error_count}")


# 运行函数
async def main():
    url = "https://www.cninfo.com.cn/new/index"

    # 单个公司处理，观察过程可以设置: headless=False
    await search_and_save_page(url, "000001", headless=True)

    # # 如果要批量处理，取消下面的注释
    # await batch_process_companies(url)


if __name__ == "__main__":
    asyncio.run(main())
