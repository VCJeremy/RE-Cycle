"""
RE-Cycle Pro - 房地产周期分析Web应用
房地产周期驾驶舱，用于分析库存周期、朱格拉周期、人口周期与资产配置
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta
import openai
import json

# 页面配置
st.set_page_config(
    page_title="RE-Cycle Pro - 房地产周期驾驶舱",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义CSS样式 - 深色金融级专业UI
st.markdown("""
<style>
    /* 全局深色主题 */
    .stApp {
        background-color: #000000;
        color: #ffffff;
    }
    
    /* 侧边栏样式 */
    section[data-testid="stSidebar"] {
        background-color: #000000;
        border-right: 1px solid #334155;
    }
    
    /* 标题样式 */
    .main-title {
        font-size: 28px;
        font-weight: 700;
        color: #f1f5f9;
        text-align: center;
        padding: 20px 0;
        border-bottom: 2px solid #3b82f6;
        margin-bottom: 20px;
    }
    
    /* 卡片样式 */
    .metric-card {
        background-color: #1a1a1a;
        border-radius: 12px;
        padding: 20px;
        border: 1px solid #334155;
        text-align: center;
        transition: all 0.3s ease;
    }
    
    .metric-card:hover {
        border-color: #3b82f6;
        transform: translateY(-2px);
    }
    
    .metric-label {
        font-size: 14px;
        color: #94a3b8;
        margin-bottom: 8px;
    }
    
    .metric-value {
        font-size: 32px;
        font-weight: 700;
        color: #f1f5f9;
    }
    
    .metric-subtitle {
        font-size: 12px;
        color: #64748b;
        margin-top: 8px;
    }
    
    /* 信号灯卡片 */
    .signal-card {
        background-color: #1a1a1a;
        border-radius: 12px;
        padding: 16px;
        border: 1px solid #334155;
        text-align: center;
        height: 100%;
    }
    
    .signal-emoji {
        font-size: 36px;
        margin-bottom: 8px;
    }
    
    .signal-name {
        font-size: 12px;
        color: #94a3b8;
        margin-bottom: 4px;
    }
    
    .signal-action {
        font-size: 14px;
        font-weight: 600;
        color: #f1f5f9;
        margin-bottom: 8px;
    }
    
    .signal-confidence {
        font-size: 11px;
        color: #64748b;
    }
    
    /* 按钮样式 */
    .stButton > button {
        background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 12px 24px;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(59, 130, 246, 0.4);
    }
    
    /* 进度条样式 */
    .confidence-bar {
        background-color: #334155;
        border-radius: 4px;
        height: 6px;
        overflow: hidden;
        margin-top: 4px;
    }
    
    .confidence-fill {
        height: 100%;
        border-radius: 4px;
        transition: width 0.5s ease;
    }
    
    /* 指标表格样式 */
    .dataframe {
        background-color: #1e293b;
        border-radius: 12px;
        overflow: hidden;
    }
    
    /* 输入框样式 */
    .stNumberInput > div > div {
        background-color: #1a1a1a;
        border-color: #333333;
        color: #ffffff;
    }
    
    /* 滑块样式 */
    .stSlider > div {
        color: #3b82f6;
    }
    
    /* 警告框样式 */
    .stAlert {
        background-color: #1e293b;
        border-color: #ef4444;
        color: #f1f5f9;
    }
    
    /* 展开器样式 */
    .streamlit-expanderHeader {
        background-color: #1e293b;
        border-radius: 8px;
        color: #f1f5f9;
    }
    
    /* 下载按钮样式 */
    .download-btn {
        background: linear-gradient(135deg, #10b981 0%, #059669 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 8px 16px;
        font-weight: 500;
    }
</style>
""", unsafe_allow_html=True)


def initialize_session_state():
    """初始化会话状态，用于数据持久化"""
    default_params = {
        'inventory': 3.5,
        'juglar': 10.0,
        'population': 30.0,
        'm1m2': -8.5,
        'investment': -10.6,
        'bond_yield': 1.91,
        'mortgage_rate': 3.85,
        'ltv': 0.7,
        'rent_yield': 2.2,
        'data_source': 'manual'
    }
    
    if 'last_params' not in st.session_state:
        st.session_state.last_params = default_params.copy()
    
    if 'analysis_result' not in st.session_state:
        st.session_state.analysis_result = None
    
    if 'api_key' not in st.session_state:
        st.session_state.api_key = ''


def calculate_cycles(params, macro_data):
    """计算周期位置和三底时间戳"""
    inventory_months = params['inventory'] * 12
    current_date = datetime.now()
    current_month = current_date.month + (current_date.year - 2026) * 12
    
    # 库存周期定位
    cycle_position = (current_month % inventory_months) / inventory_months
    
    # 确定周期相位
    if 0.75 <= cycle_position <= 1.0:
        phase = "被动去库存（复苏早期）"
        policy_bottom = "当前或已触及"
        credit_bottom = "预计2-3个季度后"
        market_bottom = "预计3-4个季度后"
    elif 0.5 <= cycle_position < 0.75:
        phase = "主动补库存（复苏中期）"
        policy_bottom = "已触及"
        credit_bottom = "当前或已触及"
        market_bottom = "预计1-2个季度后"
    elif 0.25 <= cycle_position < 0.5:
        phase = "被动补库存（过热期）"
        policy_bottom = "已触及"
        credit_bottom = "已触及"
        market_bottom = "预计4-6个季度后"
    else:
        phase = "主动去库存（衰退期）"
        policy_bottom = "预计1-2个季度后"
        credit_bottom = "预计2-4个季度后"
        market_bottom = "当前或已触及"
    
    # 计算三底时间戳（基于输入参数动态计算）
    base_year = 2026
    
    # 政策底：基于M1M2剪刀差判断
    m1m2 = macro_data['m1m2']
    if m1m2 >= -5:
        policy_q = "2026Q1"
    elif m1m2 >= -10:
        policy_q = "2026Q2"
    elif m1m2 >= -15:
        policy_q = "2026Q3"
    else:
        policy_q = "2026Q4"
    
    # 信用底：基于投资增速判断
    investment = macro_data['investment']
    if investment >= -5:
        credit_q = "2026Q3"
    elif investment >= -10:
        credit_q = "2026Q4"
    elif investment >= -15:
        credit_q = "2027Q1"
    else:
        credit_q = "2027Q2"
    
    # 市场底：基于库存周期和利率判断
    inventory = params['inventory']
    ltv = macro_data['ltv']
    mortgage_rate = macro_data['mortgage_rate']
    
    # 综合判断市场底时间
    if inventory <= 3.0 and ltv >= 0.75 and mortgage_rate <= 3.5:
        market_q = "2026Q2"
    elif inventory <= 3.5 and ltv >= 0.65:
        market_q = "2026Q4"
    elif inventory <= 4.0:
        market_q = "2027Q2"
    else:
        market_q = "2027Q4"
    
    return {
        "policy_bottom": policy_q,
        "credit_bottom": credit_q,
        "market_bottom": market_q,
        "current_phase": phase,
        "cycle_position": cycle_position,
        "inventory_months": inventory_months
    }


def calculate_asset_signals(cycle_data, macro_data, params):
    """基于周期位置和宏观数据计算6类资产信号"""
    rent_yield = macro_data['rent_yield']
    cycle_pos = cycle_data['cycle_position']
    signals = {}
    
    # 计算复苏系数（0-1，越接近1表示越接近复苏）
    recovery_factor = cycle_pos if cycle_pos > 0.5 else 1 - cycle_pos
    
    # 一二线核心区住宅
    if rent_yield > 2.5 and cycle_pos >= 0.5:
        signals['tier1_res'] = {'signal': 'green', 'action': '积极配置', 'confidence': 0.85}
    elif rent_yield < 2.0 or cycle_pos < 0.25:
        signals['tier1_res'] = {'signal': 'red', 'action': '观望等待', 'confidence': 0.75}
    else:
        signals['tier1_res'] = {'signal': 'yellow', 'action': '左侧布局', 'confidence': 0.70}
    
    # 一二线商业地产
    if rent_yield > 3.0 and cycle_pos >= 0.6:
        signals['tier1_com'] = {'signal': 'green', 'action': '关注核心', 'confidence': 0.80}
    elif rent_yield < 2.2 or cycle_pos < 0.3:
        signals['tier1_com'] = {'signal': 'red', 'action': '规避为主', 'confidence': 0.85}
    else:
        signals['tier1_com'] = {'signal': 'yellow', 'action': '谨慎关注', 'confidence': 0.65}
    
    # 二线住宅
    if rent_yield > 2.8 and cycle_pos >= 0.55:
        signals['tier2_res'] = {'signal': 'green', 'action': '择机买入', 'confidence': 0.75}
    elif rent_yield < 2.2 or cycle_pos < 0.35:
        signals['tier2_res'] = {'signal': 'red', 'action': '保持观望', 'confidence': 0.80}
    else:
        signals['tier2_res'] = {'signal': 'yellow', 'action': '精选城市', 'confidence': 0.65}
    
    # 二线商业
    if rent_yield > 3.5 and cycle_pos >= 0.65:
        signals['tier2_com'] = {'signal': 'green', 'action': '关注优质', 'confidence': 0.70}
    elif rent_yield < 2.5 or cycle_pos < 0.4:
        signals['tier2_com'] = {'signal': 'red', 'action': '规避风险', 'confidence': 0.85}
    else:
        signals['tier2_com'] = {'signal': 'yellow', 'action': '暂不考虑', 'confidence': 0.70}
    
    # 三四线住宅（人口流出压力）
    if macro_data['population'] < 28:
        signals['tier34_res'] = {'signal': 'red', 'action': '坚决回避', 'confidence': 0.90}
    elif cycle_pos >= 0.7:
        signals['tier34_res'] = {'signal': 'yellow', 'action': '核心城市', 'confidence': 0.60}
    else:
        signals['tier34_res'] = {'signal': 'red', 'action': '全面规避', 'confidence': 0.85}
    
    # 三四线商业（流动性陷阱）
    signals['tier34_com'] = {'signal': 'red', 'action': '零元购/规避', 'confidence': 0.95}
    
    return signals


def create_gantt_chart(cycle_data, signals):
    """创建Plotly甘特图"""
    # 生成时间轴数据
    quarters = []
    current_date = datetime.now()
    for i in range(12):  # 2026Q1 to 2028Q4
        q_num = (current_date.month - 1) // 3 + 1 + i
        year_offset = (q_num - 1) // 4
        q_display = q_num - year_offset * 4
        year = current_date.year + year_offset
        quarters.append(f"{year}Q{q_display}")
    
    # 资产类别
    assets = [
        '一二线核心区住宅',
        '一二线商业地产',
        '二线住宅',
        '二线商业',
        '三四线住宅',
        '三四线商业'
    ]
    
    # 颜色映射
    color_map = {
        'green': '#10b981',  # 上涨期
        'yellow': '#f59e0b', # 横盘期
        'red': '#ef4444'     # 下跌/出清期
    }
    
    # 创建甘特图数据
    fig = go.Figure()
    
    # 添加三底时间点的垂直虚线
    policy_q = cycle_data['policy_bottom']
    credit_q = cycle_data['credit_bottom']
    market_q = cycle_data['market_bottom']
    
    # 获取各季度在图表中的索引
    quarter_indices = {q: i for i, q in enumerate(quarters)}
    
    if policy_q in quarter_indices:
        fig.add_vline(x=quarter_indices[policy_q], line_dash="dash", line_color="#3b82f6", line_width=2)
        fig.add_annotation(x=quarter_indices[policy_q], y=5.5, text="政策底", showarrow=False, font=dict(color="#3b82f6", size=12))
    
    if credit_q in quarter_indices:
        fig.add_vline(x=quarter_indices[credit_q], line_dash="dash", line_color="#f97316", line_width=2)
        fig.add_annotation(x=quarter_indices[credit_q], y=5.2, text="信用底", showarrow=False, font=dict(color="#f97316", size=12))
    
    if market_q in quarter_indices:
        fig.add_vline(x=quarter_indices[market_q], line_dash="dash", line_color="#22c55e", line_width=2)
        fig.add_annotation(x=quarter_indices[market_q], y=4.9, text="市场底", showarrow=False, font=dict(color="#22c55e", size=12))
    
    # 为每个资产创建条形
    y_positions = {
        '一二线核心区住宅': 5,
        '一二线商业地产': 4,
        '二线住宅': 3,
        '二线商业': 2,
        '三四线住宅': 1,
        '三四线商业': 0
    }
    
    asset_keys = ['tier1_res', 'tier1_com', 'tier2_res', 'tier2_com', 'tier34_res', 'tier34_com']
    
    for asset_name, asset_key in zip(assets, asset_keys):
        signal = signals.get(asset_key, {'signal': 'red'})
        color = color_map[signal['signal']]
        
        # 根据信号决定显示的周期
        if signal['signal'] == 'green':
            # 绿色信号显示为上涨期
            start_idx = quarter_indices.get(cycle_data.get('market_bottom', '2026Q3'), 2)
            end_idx = min(start_idx + 5, len(quarters))
        elif signal['signal'] == 'yellow':
            # 黄色信号显示为过渡期
            start_idx = quarter_indices.get(cycle_data.get('credit_bottom', '2026Q4'), 3)
            end_idx = min(start_idx + 4, len(quarters))
        else:
            # 红色信号显示为出清期
            start_idx = 0
            end_idx = min(quarter_indices.get(cycle_data.get('market_bottom', '2027Q2'), 6), len(quarters))
        
        fig.add_trace(go.Bar(
            y=[asset_name],
            x=[end_idx - start_idx],
            base=[start_idx],
            orientation='h',
            marker_color=color,
            text=signal['action'],
            textposition='inside',
            textfont=dict(color='white', size=10),
            hovertemplate=f"{asset_name}<br>状态: {signal['action']}<br>置信度: {signal['confidence']*100:.0f}%<extra></extra>",
            showlegend=False
        ))
    
    # 更新布局
    fig.update_layout(
        title=dict(
            text='📊 房地产周期资产配置时序图（2026Q1-2028Q4）',
            font=dict(color='#f1f5f9', size=18),
            x=0.5
        ),
        xaxis=dict(
            title='时间',
            tickmode='array',
            tickvals=list(range(len(quarters))),
            ticktext=quarters,
            tickfont=dict(color='#94a3b8'),
            titlefont=dict(color='#94a3b8'),
            gridcolor='#334155',
            zerolinecolor='#334155'
        ),
        yaxis=dict(
            title='',
            tickfont=dict(color='#94a3b8'),
            gridcolor='#334155',
            zerolinecolor='#334155'
        ),
        paper_bgcolor='#0f172a',
        plot_bgcolor='#1e293b',
        font=dict(color='#e2e8f0'),
        height=400,
        margin=dict(l=20, r=20, t=60, b=40),
        showlegend=True,
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=-0.2,
            xanchor='center',
            x=0.5,
            font=dict(color='#94a3b8')
        )
    )
    
    # 添加图例说明
    fig.add_trace(go.Scatter(
        x=[None],
        y=[None],
        mode='markers',
        marker=dict(color='#10b981', size=10),
        name='上涨/配置期'
    ))
    fig.add_trace(go.Scatter(
        x=[None],
        y=[None],
        mode='markers',
        marker=dict(color='#f59e0b', size=10),
        name='横盘/观望期'
    ))
    fig.add_trace(go.Scatter(
        x=[None],
        y=[None],
        mode='markers',
        marker=dict(color='#ef4444', size=10),
        name='下跌/出清期'
    ))
    
    return fig


def create_metrics_table(cycle_data, macro_data, signals):
    """创建关键监测指标表格"""
    metrics_data = [
        {
            '指标': '库存周期位置',
            '当前值': f"{cycle_data['cycle_position']*100:.1f}%",
            '底部阈值': '>75%',
            '状态': '🟢 健康' if cycle_data['cycle_position'] > 0.75 else ('🟡 偏弱' if cycle_data['cycle_position'] > 0.5 else '🔴 去化中')
        },
        {
            '指标': 'M1M2剪刀差',
            '当前值': f"{macro_data['m1m2']:.1f}%",
            '底部阈值': '>-5%',
            '状态': '🟢 宽货币' if macro_data['m1m2'] > -5 else ('🟡 边际改善' if macro_data['m1m2'] > -10 else '🔴 紧货币')
        },
        {
            '指标': '房地产投资增速',
            '当前值': f"{macro_data['investment']:.1f}%",
            '底部阈值': '>-5%',
            '状态': '🟢 企稳' if macro_data['investment'] > -5 else ('🟡 降幅收窄' if macro_data['investment'] > -12 else '🔴 持续下滑')
        },
        {
            '指标': '10年期国债收益率',
'当前值': f"{macro_data['bond_yield']:.2f}%",
            '底部阈值': '<2.5%',
            '状态': '🟢 宽松环境' if macro_data['bond_yield'] < 2.5 else ('🟡 中性' if macro_data['bond_yield'] < 3.5 else '🔴 利率压力')
        },
        {
            '指标': '贷款利率',
            '当前值': f"{macro_data['mortgage_rate']:.2f}%",
            '底部阈值': '<4%',
            '状态': '🟢 友好' if macro_data['mortgage_rate'] < 4 else ('🟡 适中' if macro_data['mortgage_rate'] < 5 else '🔴 偏高')
        },
        {
            '指标': 'LTV贷款价值比',
            '当前值': f"{macro_data['ltv']:.2f}",
            '底部阈值': '>0.7',
            '状态': '🟢 杠杆空间' if macro_data['ltv'] > 0.7 else ('🟡 适度' if macro_data['ltv'] > 0.5 else '🔴 限制')
        }
    ]
    
    df = pd.DataFrame(metrics_data)
    return df


def generate_strategy_llm(cycle_data, signals, macro_data, api_key):
    """调用OpenAI API生成深度策略解读"""
    if not api_key:
        return None, "请先在侧边栏输入OpenAI API Key"
    
    try:
        client = openai.OpenAI(api_key=api_key)
        
        # 构建信号摘要
        signal_summary = []
        for key, value in signals.items():
            signal_summary.append(f"- {key}: {value['action']} (置信度{value['confidence']*100:.0f}%)")
        
        prompt = f"""
基于以下房地产周期数据，生成专业投资策略解读：

【周期定位】
- 当前周期相位：{cycle_data['current_phase']}
- 周期位置：{cycle_data['cycle_position']*100:.1f}%
- 政策底时间：{cycle_data['policy_bottom']}
- 信用底时间：{cycle_data['credit_bottom']}
- 市场底时间：{cycle_data['market_bottom']}

【宏观指标】
- M1M2剪刀差：{macro_data['m1m2']}%
- 房地产投资增速：{macro_data['investment']}%
- 10年期国债收益率：{macro_data['bond_yield']}%
- 贷款利率：{macro_data['mortgage_rate']}%
- LTV贷款价值比：{macro_data['ltv']}
- 租售比：{macro_data['rent_yield']}%

【资产配置信号】
{chr(10).join(signal_summary)}

请提供以下内容（使用Markdown格式）：

## 1. 当前阶段操作策略（100字内）
[策略建议]

## 2. 2026-2027年关键风险点提示
- 风险点1
- 风险点2
- 风险点3

## 3. 不同资金量配置建议
- **500万以下**：配置建议
- **500万-5000万**：配置建议  
- **5000万以上**：配置建议

请保持专业、客观的投资分析风格。
"""
        
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": "你是一位资深的房地产投资分析师，专注于宏观经济周期与房地产市场的研究。你的分析风格专业、客观、简洁，能够为投资者提供清晰、可操作的策略建议。"
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.7,
            max_tokens=1500
        )
        
        return response.choices[0].message.content, None
        
    except Exception as e:
        return None, f"API调用失败: {str(e)}"


def validate_inputs(params, macro_data):
    """验证输入数据的有效性"""
    errors = []
    
    if macro_data['m1m2'] < -20 or macro_data['m1m2'] > 10:
        errors.append("M1M2剪刀差超出合理范围（-20% ~ +10%）")
    
    if macro_data['investment'] < -20 or macro_data['investment'] > 20:
        errors.append("房地产投资增速超出合理范围（-20% ~ +20%）")
    
    if macro_data['bond_yield'] < 0.5 or macro_data['bond_yield'] > 5.0:
        errors.append("10年期国债收益率超出合理范围（0.5% ~ 5.0%）")
    
    if macro_data['mortgage_rate'] < 2.0 or macro_data['mortgage_rate'] > 8.0:
        errors.append("贷款利率超出合理范围（2.0% ~ 8.0%）")
    
    if macro_data['ltv'] < 0.3 or macro_data['ltv'] > 0.9:
        errors.append("LTV贷款价值比超出合理范围（0.3 ~ 0.9）")
    
    return errors


def main():
    """主应用函数"""
    # 初始化会话状态
    initialize_session_state()
    
    # 恢复上次保存的参数
    last_params = st.session_state.last_params
    
    # 侧边栏布局（30%宽度）
    with st.sidebar:
        st.markdown('<div class="main-title">🏠 RE-Cycle Pro<br>房地产周期驾驶舱</div>', unsafe_allow_html=True)
        
        # 数据源选择
        st.subheader("📊 数据源选择")
        data_source = st.radio(
            "选择数据获取方式：",
            ["手动输入", "自动抓取"],
            index=0 if last_params['data_source'] == 'manual' else 1,
            key='data_source'
        )
        
        if data_source == "自动抓取":
            st.info("🔄 自动抓取功能开发中，敬请期待！")
            data_source = "手动输入"
        
        st.markdown("---")
        
        # 周期参数滑块
        st.subheader("📈 周期参数配置")
        
        inventory = st.slider(
            "库存周期（年）",
            min_value=2.0,
            max_value=5.0,
            value=last_params['inventory'],
            step=0.1,
            help="房地产库存去化周期，反映市场供需关系"
        )
        
        juglar = st.slider(
            "朱格拉周期（年）",
            min_value=7.0,
            max_value=12.0,
            value=last_params['juglar'],
            step=0.5,
            help="设备投资周期，约为7-12年"
        )
        
        population = st.slider(
            "人口周期（年）",
            min_value=25.0,
            max_value=35.0,
            value=last_params['population'],
            step=1.0,
            help="人口结构变化周期，通常为25-35年"
        )
        
        st.markdown("---")
        
        # 宏观数据输入
        st.subheader("📉 宏观数据输入")
        
        m1m2 = st.number_input(
            "M1M2剪刀差（%）",
            min_value=-20.0,
            max_value=10.0,
            value=last_params['m1m2'],
            step=0.1,
            help="反映货币供应的宽松程度，M1增速-M2增速"
        )
        
        investment = st.number_input(
            "房地产投资增速（%）",
            min_value=-20.0,
            max_value=20.0,
            value=last_params['investment'],
            step=0.1,
            help="房地产开发投资同比增速"
        )
        
        bond_yield = st.number_input(
            "10年期国债收益率（%）",
            min_value=0.5,
            max_value=5.0,
            value=last_params['bond_yield'],
            step=0.01,
            help="无风险利率水平，影响房地产资产定价"
        )
        
        mortgage_rate = st.number_input(
            "贷款利率（%）",
            min_value=2.0,
            max_value=8.0,
            value=last_params['mortgage_rate'],
            step=0.01,
            help="购房贷款利率，影响购买力"
        )
        
        ltv = st.number_input(
            "LTV贷款价值比",
            min_value=0.3,
            max_value=0.9,
            value=last_params['ltv'],
            step=0.05,
            help="贷款成数，首付比例的反面"
        )
        
        rent_yield = st.number_input(
            "租售比（%）",
            min_value=1.5,
            max_value=4.0,
            value=last_params['rent_yield'],
            step=0.1,
            help="年租金/房价，衡量房产投资回报"
        )
        
        st.markdown("---")
        
        # API Key输入
        st.subheader("🔑 API配置")
        api_key = st.text_input(
            "OpenAI API Key（仅用于深度策略解读）",
            type="password",
            value=st.session_state.get('api_key', ''),
            help="输入API Key后可以使用AI策略解读功能"
        )
        st.session_state.api_key = api_key
        
        # 生成报告按钮
        st.markdown("<br>", unsafe_allow_html=True)
        generate_btn = st.button("📊 生成周期分析报告", use_container_width=True)
    
    # 主区域布局（70%宽度）
    col1, col2, col3 = st.columns([1, 1, 1])
    
    # 收集参数
    params = {
        'inventory': inventory,
        'juglar': juglar,
        'population': population,
        'data_source': 'manual'
    }
    
    macro_data = {
        'm1m2': m1m2,
        'investment': investment,
        'bond_yield': bond_yield,
        'mortgage_rate': mortgage_rate,
        'ltv': ltv,
        'rent_yield': rent_yield
    }
    
    # 验证输入
    errors = validate_inputs(params, macro_data)
    
    if errors:
        for error in errors:
            st.error(f"⚠️ 数据异常: {error}")
    
    # 计算逻辑
    if generate_btn or st.session_state.analysis_result is not None:
        if generate_btn:
            # 保存参数到会话状态
            st.session_state.last_params = {
                'inventory': inventory,
                'juglar': juglar,
                'population': population,
                'm1m2': m1m2,
                'investment': investment,
                'bond_yield': bond_yield,
                'mortgage_rate': mortgage_rate,
                'ltv': ltv,
                'rent_yield': rent_yield,
                'data_source': 'manual'
            }
            
            # 显示加载状态
            with st.spinner("正在计算周期位置..."):
                cycle_data = calculate_cycles(params, macro_data)
            
            with st.spinner("正在分析资产配置..."):
                signals = calculate_asset_signals(cycle_data, macro_data, params)
            
            # 保存结果
            st.session_state.analysis_result = {
                'cycle_data': cycle_data,
                'signals': signals,
                'params': params,
                'macro_data': macro_data
            }
        else:
            # 恢复上次结果
            result = st.session_state.analysis_result
            cycle_data = result['cycle_data']
            signals = result['signals']
        
        # 顶部：三底时间线卡片
        with col1:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">🏛️ 政策底</div>
                <div class="metric-value">{cycle_data['policy_bottom']}</div>
                <div class="metric-subtitle">货币政策转向信号</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">💳 信用底</div>
                <div class="metric-value">{cycle_data['credit_bottom']}</div>
                <div class="metric-subtitle">信贷宽松传导到位</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">🏠 市场底</div>
                <div class="metric-value">{cycle_data['market_bottom']}</div>
                <div class="metric-subtitle">成交量企稳回升</div>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # 当前周期相位
        st.info(f"📍 **{cycle_data['current_phase']}**")
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # 中部：Plotly甘特图
        with st.spinner("正在渲染资产配置时序图..."):
            gantt_fig = create_gantt_chart(cycle_data, signals)
            st.plotly_chart(gantt_fig, use_container_width=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # 下部：两列布局
        left_col, right_col = st.columns([1, 1])
        
        # 左列：六类资产配置信号灯
        with left_col:
            st.subheader("🚦 资产配置信号灯")
            
            signal_cols = st.columns(2)
            signal_items = [
                ('tier1_res', '一二线核心区住宅', '一二线住宅'),
                ('tier1_com', '一二线商业地产', '一二线商业'),
                ('tier2_res', '二线住宅', '二线住宅'),
                ('tier2_com', '二线商业', '二线商业'),
                ('tier34_res', '三四线住宅', '三四线住宅'),
                ('tier34_com', '三四线商业', '三四线商业')
            ]
            
            emoji_map = {
                'green': '🟢',
                'yellow': '🟡',
                'red': '🔴'
            }
            
            confidence_colors = {
                'green': '#10b981',
                'yellow': '#f59e0b',
                'red': '#ef4444'
            }
            
            for i, (key, name, short_name) in enumerate(signal_items):
                col = signal_cols[i % 2]
                signal = signals.get(key, {'signal': 'red', 'action': '未知', 'confidence': 0.5})
                
                with col:
                    st.markdown(f"""
                    <div class="signal-card">
                        <div class="signal-emoji">{emoji_map.get(signal['signal'], '🔴')}</div>
                        <div class="signal-name">{short_name}</div>
                        <div class="signal-action">{signal['action']}</div>
                        <div class="signal-confidence">置信度 {signal['confidence']*100:.0f}%</div>
                        <div class="confidence-bar">
                            <div class="confidence-fill" style="width: {signal['confidence']*100}%; background-color: {confidence_colors.get(signal['signal'], '#ef4444')};"></div>
                        </div>
                    </div>
                    <br>
                    """, unsafe_allow_html=True)
        
        # 右列：关键监测指标表格
        with right_col:
            st.subheader("📋 关键监测指标")
            
            metrics_df = create_metrics_table(cycle_data, macro_data, signals)
            
            # 显示表格
            st.dataframe(
                metrics_df,
                hide_index=True,
                use_container_width=True,
                column_config={
                    '指标': st.column_config.TextColumn('指标', width='medium'),
                    '当前值': st.column_config.TextColumn('当前值', width='small'),
                    '底部阈值': st.column_config.TextColumn('底部阈值', width='small'),
                    '状态': st.column_config.TextColumn('状态', width='medium')
                }
            )
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # AI策略解读展开器
        with st.expander("🤖 AI策略解读（基于GPT-4）", expanded=False):
            st.markdown("""
            <div style="background-color: #1e293b; padding: 16px; border-radius: 12px; margin-bottom: 16px;">
                <p style="color: #94a3b8; font-size: 14px; margin: 0;">
                    💡 AI策略解读基于您当前的周期参数和宏观数据生成，仅供参考，不构成投资建议。
                    生成策略解读需要调用OpenAI API，请确保已在侧边栏输入有效的API Key。
                </p>
            </div>
            """, unsafe_allow_html=True)
            
            if 'llm_result' not in st.session_state:
                st.session_state.llm_result = None
            
            if 'llm_params_hash' not in st.session_state:
                st.session_state.llm_params_hash = None
            
            # 检查参数是否变化
            current_hash = hash(json.dumps({'cycle': cycle_data, 'signals': signals, 'macro': macro_data}, sort_keys=True))
            
            if st.button("🎯 生成深度解读"):
                with st.spinner("正在调用AI生成策略解读..."):
                    llm_result, error = generate_strategy_llm(cycle_data, signals, macro_data, api_key)
                    
                    if error:
                        st.error(f"❌ {error}")
                    else:
                        st.session_state.llm_result = llm_result
                        st.session_state.llm_params_hash = current_hash
                        st.rerun()
            
            # 显示结果（如果参数未变化）
            if st.session_state.llm_result and st.session_state.llm_params_hash == current_hash:
                st.markdown(st.session_state.llm_result)
            
            elif st.session_state.llm_result and st.session_state.llm_params_hash != current_hash:
                st.info("📊 参数已变化，请点击「生成深度解读」获取最新策略")
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # 导出报告功能
        st.subheader("📄 报告导出")
        
        report_content = f"""
# RE-Cycle Pro 房地产周期分析报告
生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 一、周期定位

| 周期类型 | 时间 | 说明 |
|---------|------|------|
| 政策底 | {cycle_data['policy_bottom']} | 货币政策转向信号 |
| 信用底 | {cycle_data['credit_bottom']} | 信贷宽松传导到位 |
| 市场底 | {cycle_data['market_bottom']} | 成交量企稳回升 |

**当前周期相位**：{cycle_data['current_phase']}

## 二、宏观指标

| 指标 | 当前值 | 健康区间 | 状态 |
|------|--------|---------|------|
| M1M2剪刀差 | {macro_data['m1m2']}% | >-5% | {'🟢 宽货币' if macro_data['m1m2'] > -5 else ('🟡 边际改善' if macro_data['m1m2'] > -10 else '🔴 紧货币')} |
| 投资增速 | {macro_data['investment']}% | >-5% | {'🟢 企稳' if macro_data['investment'] > -5 else ('🟡 降幅收窄' if macro_data['investment'] > -12 else '🔴 持续下滑')} |
| 国债收益率 | {macro_data['bond_yield']}% | <2.5% | {'🟢 宽松' if macro_data['bond_yield'] < 2.5 else ('🟡 中性' if macro_data['bond_yield'] < 3.5 else '🔴 压力')} |
| 贷款利率 | {macro_data['mortgage_rate']}% | <4% | {'🟢 友好' if macro_data['mortgage_rate'] < 4 else ('🟡 适中' if macro_data['mortgage_rate'] < 5 else '🔴 偏高')} |
| LTV贷款比 | {macro_data['ltv']} | >0.7 | {'🟢 空间' if macro_data['ltv'] > 0.7 else ('🟡 适度' if macro_data['ltv'] > 0.5 else '🔴 限制')} |

## 三、资产配置信号

| 资产类别 | 信号 | 操作建议 | 置信度 |
|---------|------|---------|--------|
| 一二线核心区住宅 | {emoji_map.get(signals['tier1_res']['signal'], '🔴')} | {signals['tier1_res']['action']} | {signals['tier1_res']['confidence']*100:.0f}% |
| 一二线商业地产 | {emoji_map.get(signals['tier1_com']['signal'], '🔴')} | {signals['tier1_com']['action']} | {signals['tier1_com']['confidence']*100:.0f}% |
| 二线住宅 | {emoji_map.get(signals['tier2_res']['signal'], '🔴')} | {signals['tier2_res']['action']} | {signals['tier2_res']['confidence']*100:.0f}% |
| 二线商业 | {emoji_map.get(signals['tier2_com']['signal'], '🔴')} | {signals['tier2_com']['action']} | {signals['tier2_com']['confidence']*100:.0f}% |
| 三四线住宅 | {emoji_map.get(signals['tier34_res']['signal'], '🔴')} | {signals['tier34_res']['action']} | {signals['tier34_res']['confidence']*100:.0f}% |
| 三四线商业 | {emoji_map.get(signals['tier34_com']['signal'], '🔴')} | {signals['tier34_com']['action']} | {signals['tier34_com']['confidence']*100:.0f}% |

---
*报告由 RE-Cycle Pro 自动生成*
"""
        
        st.download_button(
            label="📥 下载PDF报告",
            data=report_content,
            file_name=f"RE_Cycle_Report_{datetime.now().strftime('%Y%m%d')}.md",
            mime="text/markdown",
            use_container_width=True
        )
    
    else:
        # 初始状态显示欢迎信息
        st.markdown("""
        <div style="background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); padding: 40px; border-radius: 16px; text-align: center; margin: 40px 0;">
            <h2 style="color: #f1f5f9; margin-bottom: 16px;">🏠 欢迎使用 RE-Cycle Pro</h2>
            <p style="color: #94a3b8; font-size: 16px; line-height: 1.8;">
                RE-Cycle Pro 是一款专业的房地产周期分析工具，<br>
                通过分析库存周期、朱格拉周期、人口周期与宏观经济指标，<br>
                为您提供科学的资产配置建议。
            </p>
            <div style="margin-top: 24px; display: flex; justify-content: center; gap: 16px; flex-wrap: wrap;">
                <span style="background-color: #3b82f6; color: white; padding: 8px 16px; border-radius: 20px; font-size: 14px;">📊 周期定位</span>
                <span style="background-color: #10b981; color: white; padding: 8px 16px; border-radius: 20px; font-size: 14px;">🎯 资产配置</span>
                <span style="background-color: #f59e0b; color: white; padding: 8px 16px; border-radius: 20px; font-size: 14px;">🤖 AI策略</span>
                <span style="background-color: #8b5cf6; color: white; padding: 8px 16px; border-radius: 20px; font-size: 14px;">📈 可视化</span>
            </div>
            <p style="color: #64748b; font-size: 14px; margin-top: 32px;">
                👈 请在左侧边栏配置参数，然后点击「生成周期分析报告」开始分析
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        # 显示默认的周期说明
        st.subheader("📚 周期理论说明")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("""
            <div class="metric-card">
                <div class="metric-label">📦 库存周期</div>
                <div style="color: #e2e8f0; font-size: 13px; line-height: 1.6;">
                    2-5年，去化库存的周期，反映市场供需关系变化
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown("""
            <div class="metric-card">
                <div class="metric-label">⚙️ 朱格拉周期</div>
                <div style="color: #e2e8f0; font-size: 13px; line-height: 1.6;">
                    7-12年，设备投资周期，影响经济整体活跃度
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown("""
            <div class="metric-card">
                <div class="metric-label">👥 人口周期</div>
                <div style="color: #e2e8f0; font-size: 13px; line-height: 1.6;">
                    25-35年，人口结构周期，长期决定房地产需求
                </div>
            </div>
            """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
