"""
查询岗位的薪资水平：薪资公平：可以爬取：aiohttp版
"""
import json
import random
import time

import aiofiles
import aiohttp
import asyncio

from aiohttp import ClientTimeout
from bs4 import BeautifulSoup

# 基础配置
TIMEOUT = 120
timeout = ClientTimeout(total=TIMEOUT)


async def load_stock_codes():
    """加载岗位代码和名称"""
    async with aiofiles.open("data/stock_codes_mini.txt", "r") as f:
        codes = []
        async for line in f:
            if not line.strip():
                continue
            cs = json.loads(line)
            codes.append(cs)
        return codes


def get_education_level(topic_box):
    """
    从topicBox前面的a标签中获取教育水平
    """
    # 查找前一个兄弟元素，可能是a标签
    prev_element = topic_box.find_previous_sibling('a', class_='slideToggle')

    if prev_element:
        # 在a标签中查找h2标签
        h2_element = prev_element.find('h2', class_='jobEducationTitle')
        if h2_element:
            # h2中有多个span，第二个是教育水平
            spans = h2_element.find_all('span')
            if len(spans) >= 2:
                return spans[1].get_text(strip=True)

    return "未知教育水平"


def extract_salary_data(html_content):
    """
    按照指定路径提取薪资数据
    """
    soup = BeautifulSoup(html_content, 'html.parser')

    # 1. 先找到 <div id="main_pnlDesc">
    main_container = soup.find('div', id='main_pnlDesc')

    if not main_container:
        print("未找到 main_pnlDesc 容器")
        return []

    # 2. 再找到它下面的所有 <div class="topicContentBox">
    topic_boxes = main_container.find_all('div', class_='topicContentBox')

    results = []

    for topic_box in topic_boxes:
        # 获取对应的教育水平（从前面的a标签中获取）
        education_level = get_education_level(topic_box)

        # 3.1 找到 <div class="avgSalaryListPart01">，提取ol>li的文本内容
        years_part = topic_box.find('div', class_='avgSalaryListPart01')
        years = []
        if years_part:
            years_ol = years_part.find('ol')
            if years_ol:
                years_li = years_ol.find_all('li')
                years = [li.get_text(strip=True) for li in years_li]

        # 3.2 找到 <div class="avgSalaryListPart02">，提取ol>li的文本内容
        salary_part = topic_box.find('div', class_='avgSalaryListPart02')
        salaries = []
        if salary_part:
            salary_ol = salary_part.find('ol')
            if salary_ol:
                salary_li = salary_ol.find_all('li')
                salaries = [li.get_text(strip=True) for li in salary_li]

        # 确保数据对应且不为空
        if years and salaries and len(years) == len(salaries):
            results.append({
                'education_level': education_level,
                'years': years,
                'salaries': salaries
            })

    return results


async def get_salary_executives(scode: str, sname: str = ""):
    """
    获取公司高管信息

    Args:
        scode: 岗位代码，如"110101"
        sname: 岗位名称，如"金融專業主管"
    """
    url = f"https://www.jobsalary.com.tw/salarysummary.aspx?codeNo={scode}"
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        # "Referer": "https://www.cninfo.com.cn/"
    }
    # params = {"scode": scode}
    print(f"正在请求：{url}: {scode}: {sname}")

    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            # async with session.get(url, headers=headers, ssl=False) as response:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    html = await response.text()
                    results = extract_salary_data(html)
                    return results
                else:
                    print(f"请求失败，状态码: {response.status}")
                    return None
    except Exception as e:
        print(f"发生错误: {e}")
        return None


# 使用示例
async def main():
    # # 查询金融專業主管
    # result = await get_salary_executives("110101", "金融專業主管")
    # print(json.dumps(result, ensure_ascii=False, indent=2))

    t1 = time.time()

    # 批量获取
    jobs = await load_stock_codes()
    n = 10
    print(f"加载到岗位数量：{len(jobs)}: 处理前{n}：{jobs[:n]}")
    print("-" * 10)
    total_count = len(jobs[:n])
    success_count = 0
    error_count = 0
    user_count = 0
    for i, row in enumerate(jobs[:n]):
        s_code = row["codeNo"]
        name = row["name"]
        results = await get_salary_executives(s_code, name)
        if not results:
            print(f"#{i + 1}/{total_count}({s_code}-{name}: 0条记录！")
            error_count += 1
        else:
            print(f"#{i + 1}/{total_count}({s_code}-{name}:{len(results)}条薪资信息)：")
            if results:
                for dic1 in results:
                    print(f"# {dic1['education_level']} 平均薪資：")
                    print(dic1["years"])
                    print(dic1["salaries"])
                success_count += 1
                user_count += len(results)
            else:
                error_count += 1
        print("-" * 30)
        await asyncio.sleep(random.randint(3, 6))

    t2 = time.time()
    print(f"全部处理完成，耗时：{t2 - t1:.3f}秒")
    print(f"总岗位数：{total_count}, 成功数量: {success_count}, 失败数量: {error_count}")
    print(f"总岗位薪资数量：{user_count}条")


if __name__ == "__main__":
    asyncio.run(main())
