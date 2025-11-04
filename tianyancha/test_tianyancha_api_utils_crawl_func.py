"""
安装依赖库: pip install 'aiohttp[speedups]'
"""
from utils.tianyancha_api_utils import crawl

# 查询公司: 支持：公司名称、公司id、注册号或社会统一信用代码
# load_test为True、可以加载测试数据进行测试，否则正式接口，需要充值和更换里面的token
rs = crawl("中航重机股份有限公司", True)
# rs = crawl("TCL科技")
print(rs)
print("---")
print("查看markdown部分")
print(rs["result"])
