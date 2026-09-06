import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import io

# ================= 1. 数据库初始化 =================
def init_db():
    conn = sqlite3.connect('hospital_logistics.db', check_same_thread=False)
    c = conn.cursor()
    # 巡查记录表
    c.execute('''CREATE TABLE IF NOT EXISTS inspections
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  date TEXT, department TEXT, 
                  water TEXT, electricity TEXT, oxygen TEXT, remarks TEXT)''')
    # 维修记录表 (新增报修人 reporter)
    c.execute('''CREATE TABLE IF NOT EXISTS maintenance
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  date TEXT, department TEXT, reporter TEXT, issue TEXT, 
                  status TEXT, progress TEXT)''')
    
    # 兼容老数据库：尝试添加 reporter 字段（如果字段已存在会报错，直接忽略）
    try:
        c.execute("ALTER TABLE maintenance ADD COLUMN reporter TEXT")
        conn.commit()
    except:
        pass
        
    conn.commit()
    return conn

conn = init_db()

# ================= 2. 页面与侧边栏配置 =================
st.set_page_config(page_title="医院后勤巡查与报修系统", layout="wide")
st.sidebar.title("🏥 后勤管理菜单")
menu = st.sidebar.radio("请选择功能模块：", ["📊 今日概览", "📝 每日巡查登记", "🔧 故障报修与进度", "📤 数据导出与报表"])

# 科室列表（已更新妇幼保健院科室）
departments = [
    "急诊科", "重症医学科(ICU)", "内科病区", "外科病区", "手术室", 
    "门诊部", "放射科", "检验科", "药剂科", 
    "围保科", "妇女保健科", "儿保科", "婚保科", 
    "供应室", "影像科", "院办公室", "妇产科", "儿科"
]

# ================= 3. 功能模块开发 =================

if menu == "📊 今日概览":
    st.header("📊 后勤运行实时概览")
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("待处理维修任务")
        # 增加查询报修人
        pending_df = pd.read_sql_query("SELECT date as 日期, department as 科室, reporter as 报修人, issue as 故障描述, status as 状态 FROM maintenance WHERE status != '已完成'", conn)
        if pending_df.empty:
            st.success("🎉 当前没有待处理的维修任务！")
        else:
            st.dataframe(pending_df, use_container_width=True, hide_index=True)
            
    with col2:
        st.subheader("今日巡查记录")
        today = datetime.now().strftime("%Y-%m-%d")
        insp_df = pd.read_sql_query(f"SELECT department as 科室, water as 水, electricity as 电, oxygen as 氧气 FROM inspections WHERE date = '{today}'", conn)
        if insp_df.empty:
            st.warning("⚠️ 今日尚未提交任何巡查记录")
        else:
            st.dataframe(insp_df, use_container_width=True, hide_index=True)

elif menu == "📝 每日巡查登记":
    st.header("📝 水电氧每日巡查登记")
    st.info("请巡查人员如实填写各科室基础设施运行情况。")
    
    with st.form("inspection_form"):
        col1, col2 = st.columns(2)
        with col1:
            insp_date = st.date_input("巡查日期", datetime.now())
            dept = st.selectbox("巡查区域/科室", departments)
        with col2:
            water = st.radio("💧 供水系统", ["正常", "异常"], horizontal=True)
            elec = st.radio("⚡ 供电系统", ["正常", "异常"], horizontal=True)
            oxy = st.radio("💨 集中供氧", ["正常", "异常"], horizontal=True)
            
        remarks = st.text_input("备注说明（如有异常请简述）")
        submit = st.form_submit_button("提交巡查记录", type="primary")
        
        if submit:
            c = conn.cursor()
            c.execute("INSERT INTO inspections (date, department, water, electricity, oxygen, remarks) VALUES (?, ?, ?, ?, ?, ?)",
                      (insp_date.strftime("%Y-%m-%d"), dept, water, elec, oxy, remarks))
            conn.commit()
            st.success(f"{dept} 的巡查记录已成功保存！")

elif menu == "🔧 故障报修与进度":
    st.header("🔧 故障报修与进度追踪")
    
    tab1, tab2 = st.tabs(["🆕 提交新报修", "🔄 进度管理 (支持实时修改)"])
    
    with tab1:
        with st.form("maintenance_form"):
            col1, col2 = st.columns(2)
            with col1:
                rep_date = st.date_input("报修日期", datetime.now())
                rep_dept = st.selectbox("报修科室", departments)
            with col2:
                # 增加报修人自填选项
                reporter = st.text_input("报修人姓名 (必填)", placeholder="请输入您的姓名")
                
            issue = st.text_area("故障详细描述", placeholder="例如：洗手池漏水、2号病房插座无电...")
            submit_rep = st.form_submit_button("提交报修单", type="primary")
            
            if submit_rep:
                if not reporter.strip():
                    st.error("请填写报修人姓名！")
                elif not issue.strip():
                    st.error("请填写故障描述！")
                else:
                    c = conn.cursor()
                    c.execute("INSERT INTO maintenance (date, department, reporter, issue, status, progress) VALUES (?, ?, ?, ?, ?, ?)",
                              (rep_date.strftime("%Y-%m-%d"), rep_dept, reporter, issue, "待处理", "已接单，等待派工"))
                    conn.commit()
                    st.success("✅ 报修已提交！后勤将尽快处理。")
                
    with tab2:
        st.markdown("💡 **操作提示：** 在下方表格中，直接双击 **“状态”** 和 **“最新进度”** 列进行修改。修改完成后，**必须点击下方保存按钮** 才能生效。")
        maint_df = pd.read_sql_query("SELECT id, date as 日期, department as 科室, reporter as 报修人, issue as 故障描述, status as 状态, progress as 最新进度 FROM maintenance", conn)
        
        if not maint_df.empty:
            edited_df = st.data_editor(
                maint_df,
                column_config={
                    "id": None, 
                    "状态": st.column_config.SelectboxColumn("状态", options=["待处理", "维修中", "已完成"], required=True),
                    "最新进度": st.column_config.TextColumn("最新进度")
                },
                disabled=["日期", "科室", "报修人", "故障描述"], 
                use_container_width=True,
                hide_index=True,
                key="maint_editor"
            )
            
            if st.button("💾 确认保存修改", type="primary"):
                c = conn.cursor()
                for index, row in edited_df.iterrows():
                    # 对比旧数据，避免全量更新
                    old_status = maint_df.loc[index, "状态"]
                    old_progress = maint_df.loc[index, "最新进度"]
                    if row["状态"] != old_status or row["最新进度"] != old_progress:
                        c.execute("UPDATE maintenance SET status=?, progress=? WHERE id=?", 
                                  (row["状态"], row["最新进度"], maint_df.loc[index, "id"]))
                conn.commit()
                st.success("✅ 进度已同步更新！各科室刷新网页即可看到最新状态。")
                # 强制刷新页面，解决状态修改没反应的问题
                st.rerun()
        else:
            st.info("暂无报修记录。")

elif menu == "📤 数据导出与报表":
    st.header("📤 数据导出与报表")
    
    # 增加管理员权限验证
    st.warning("🔒 数据导出涉及医院运行数据，仅限后勤管理员操作。")
    admin_pwd = st.text_input("请输入管理员密码：", type="password", placeholder="请输入导出密码")
    
    # 密码验证成功后才显示导出功能 (默认密码设置为: admin123)
    if admin_pwd == "admin123":
        st.success("✅ 密码正确，已解锁导出权限。")
        st.markdown("---")
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📝 巡查记录导出")
            df_insp = pd.read_sql_query("SELECT date as 日期, department as 科室, water as 供水, electricity as 供电, oxygen as 供氧, remarks as 备注 FROM inspections ORDER BY date DESC", conn)
            if not df_insp.empty:
                st.dataframe(df_insp.head(3), use_container_width=True, hide_index=True) 
                
                output_insp = io.BytesIO()
                with pd.ExcelWriter(output_insp, engine='openpyxl') as writer:
                    df_insp.to_excel(writer, index=False, sheet_name='巡查记录')
                
                st.download_button(
                    label="📥 一键下载 [巡查记录] Excel",
                    data=output_insp.getvalue(),
                    file_name=f"后勤巡查记录_{datetime.now().strftime('%Y%m%d')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    type="primary"
                )
            else:
                st.warning("系统暂无巡查记录数据。")

        with col2:
            st.subheader("🔧 维修记录导出")
            # 导出字段增加报修人
            df_maint = pd.read_sql_query("SELECT date as 报修日期, department as 科室, reporter as 报修人, issue as 故障描述, status as 处理状态, progress as 最新进度 FROM maintenance ORDER BY date DESC", conn)
            if not df_maint.empty:
                st.dataframe(df_maint.head(3), use_container_width=True, hide_index=True) 
                
                output_maint = io.BytesIO()
                with pd.ExcelWriter(output_maint, engine='openpyxl') as writer:
                    df_maint.to_excel(writer, index=False, sheet_name='维修记录')
                
                st.download_button(
                    label="📥 一键下载 [维修记录] Excel",
                    data=output_maint.getvalue(),
                    file_name=f"后勤维修记录_{datetime.now().strftime('%Y%m%d')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    type="primary"
                )
            else:
                st.warning("系统暂无维修记录数据。")
    elif admin_pwd != "":
        st.error("❌ 密码错误，无法导出数据。")
