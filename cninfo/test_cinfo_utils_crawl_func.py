"""
安装依赖库: pip install 'aiohttp[speedups]'
"""
from utils.cninfo_utils import crawl

# # 查询高管
# # rs = crawl("谢永林")
# rs = crawl("李东生")
# print(rs)

# # 查询公司: 方式1：公司代码
# rs = crawl("000001")
rs = crawl("000100")
print(rs)

# 查询公司: 方式1：公司名称
# rs = crawl("平安银行")
# rs = crawl("TCL科技")
# print(rs)
