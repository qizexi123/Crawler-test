"""
通过公司找股东：巨潮：可以爬取：aiohttp版
"""
import random
import time

import aiofiles
import aiohttp
import asyncio


async def load_stock_codes():
    """加载公司代码（股票代码）"""
    async with aiofiles.open("data/stock_codes_mini.txt", "r") as f:
        codes = []
        async for line in f:
            cs = line.split(",")
            codes += [c.strip() for c in cs if c.strip()]
        return codes


async def get_company_executives(scode: str):
    """
    获取公司高管信息

    Args:
        scode: 股票代码，如 '000001'
    """
    url = f"https://www.cninfo.com.cn/data20/companyOverview/getCompanyExecutives?scode={scode}"
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Referer": "https://www.cninfo.com.cn/"
    }
    # params = {"scode": scode}
    print(f"正在请求：{url}: {scode}")

    try:
        async with aiohttp.ClientSession() as session:
            # async with session.get(url, params=params, headers=headers, ssl=False) as response:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return data
                else:
                    print(f"请求失败，状态码: {response.status}")
                    return None
    except Exception as e:
        print(f"发生错误: {e}")
        return None


# 使用示例
async def main():
    # # 查询平安银行
    # result = await get_company_executives("000001")
    # print(json.dumps(result, ensure_ascii=False, indent=2))

    # 查询其他股票
    # result2 = await get_company_executives("000002")
    # result3 = await get_company_executives("600036")

    t1 = time.time()

    # 批量获取
    companies = await load_stock_codes()
    n = 10
    print(f"加载到公司代码数量：{len(companies)}: 处理前{n}：{companies[:n]}")
    print("-" * 10)
    total_count = len(companies[:n])
    success_count = 0
    error_count = 0
    user_count = 0
    for i, s_code in enumerate(companies[:n]):
        result = await get_company_executives(s_code)
        if not result:
            print(f"#{i + 1}/{total_count}({s_code}:0条高管信息)：可能已经退市等！")
            error_count += 1
        else:
            records = result.get('data', {}).get('records')
            print(f"#{i + 1}/{total_count}({s_code}:{len(records)}条高管信息)：{records}")
            if records:
                success_count += 1
                user_count += len(records)
            else:
                error_count += 1
        print("-" * 30)
        await asyncio.sleep(random.randint(3, 6))

    t2 = time.time()
    print(f"全部处理完成，耗时：{t2 - t1:.3f}秒")
    print(f"总公司数：{total_count}, 成功数量: {success_count}, 失败数量: {error_count}")
    print(f"总公司高管数量：{user_count}条")


if __name__ == "__main__":
    asyncio.run(main())
