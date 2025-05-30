# 网格交易大师 (GTA)

一款功能强大的股票数据观测、分析和AI小助手工具，基于中间价理念，帮助投资者快速分析股票价格走势、振幅变化及制定网格交易策略。

## 主要功能

### 市场分析工具

- **历史价格数据抓取**：自动获取股票的开盘价、收盘价、最高价、最低价和中间价数据
- **中间价分析**：计算并展示基于(最高价+最低价)/2的中间价指标与振幅分析
- **可视化图表**：K线图与中间价曲线结合展示，支持图表缩放和数据细节查看

### DeepSeek AI智能助手

- **AI交易咨询**：与DeepSeek大模型进行交易策略讨论和市场分析
- **多模型支持**：提供推理增强、通用对话和代码专家等多种模型
- **数据上传与分析**：可上传股票数据文件给AI进行深度分析
- **枢纽点策略支持**：支持计算枢纽点和支撑/阻力位，辅助网格交易决策
  

![微信截图_20250525183908](https://github.com/user-attachments/assets/6af58bd8-aebd-42bc-8664-df0e737a6f32)

![微信截图_20250525200009](https://github.com/user-attachments/assets/e9505a82-3022-46f5-9f4e-f238deaf6675)

![微信截图_20250525200119](https://github.com/user-attachments/assets/23e43437-4fa9-4826-a1dc-a1493749d327)



## 更新日志

-5月25日
-新增Deepseek的AI对话功能，须自行注册api并填入key

-5月15日
-新增了成交量与K线图


## 安装指南

1. 克隆本仓库
2. 安装依赖项：
```
pip install -r requirements.txt
```
3. 运行主应用：
```
python app.py
```
4. 在浏览器中访问：`http://localhost:8050`

**注意**：使用DeepSeek AI功能需要注册DeepSeek API密钥，并在首次使用时在应用中输入。

## 数据源

本工具当前支持以下数据源：
- **东方财富API**（默认）：无需注册，自动获取A股数据

## 使用说明

### 市场分析工具

1. 在搜索框中输入股票代码或名称（例如：603019 或 中科曙光）
2. 从下拉菜单中选择日期范围（支持多种预设时间段和自定义区间）
3. 点击“查询”按钮获取并分析股票数据
4. 在主界面查看K线图、中间价曲线和振幅分析
5. 通过数据表格查看详细的交易数据和技术指标
6. 系统会自动生成基于预设阈值的交易预警信息

### DeepSeek AI对话功能

1. 点击顶部的“DeepSeek对话”标签页进入AI对话界面
2. 首次使用需在左侧面板输入DeepSeek API密钥并点击“保存”
3. 选择合适的模型（默认为DeepSeek-R1推理增强模型）
4. 在对话框中输入问题，通过点击“发送”按钮或直接按回车键发送消息
5. 如需分析当前股票数据，可点击“上传当前股票数据到对话”按钮

#### 枢纽点策略分析示例问题

- “请分析这支股票的枢纽点”
- “如何利用枢纽点制定网格交易策略”
- “基于上传的数据计算枢纽点和支撑/阻力位”

## 项目结构

### 核心文件

- `app.py`: 主应用入口和Dash界面实现
- `data_fetcher.py`: 股票数据获取模块，支持多种数据源接口
- `data_processor.py`: 数据处理和技术指标计算模块
- `visualizer.py`: 数据可视化和图表生成模块
- `strategy.py`: 交易策略实现和回测框架
- `utils.py`: 通用工具函数和辅助方法

### DeepSeek AI模块

- `deepseek_api.py`: DeepSeek API调用模块，处理与AI模型的交互
- `deepseek_ui.py`: DeepSeek对话界面实现，提供对话组件和回调函数
- `chattemp/`: 对话历史缓存目录
- `key.txt`: API密钥存储文件（首次使用时会自动创建）

### 其他资源

- `assets/`: 静态资源目录，包含网站图标、CSS样式等资源
- `temp/`: 临时数据文件存储目录

## 技术特点

- **现代化UI**：采用Dash和Bootstrap组件构建直观易用的界面
- **响应式设计**：适配不同屏幕尺寸，支持移动设备访问
- **实时数据处理**：高效的数据计算和展示流程
- **交互式图表**：支持放大缩小、数据选择和详情查看

