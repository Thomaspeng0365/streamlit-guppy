import streamlit as st
import gspread
import pandas as pd

# 從 Streamlit secrets 讀取 Google 服務帳號憑證
try:
    creds = st.secrets["gcp_service_account"]
    gc = gspread.service_account_from_dict(creds)
except Exception as e:
    st.error(f"無法連接到 Google Sheets。請檢查 .streamlit/secrets.toml 檔案和服務帳號權限。錯誤：{e}")
    st.stop()

def get_sheet_data():
    """連接並取得 Google Sheet 的資料。"""
    try:
        # 開啟你的 Google Sheet，請將 '拯救會員管理' 替換為你的表格名稱
        worksheet = gc.open("拯救會員管理").sheet1
        return worksheet
    except Exception as e:
        st.error(f"無法開啟 Google Sheet。請確認服務帳號已獲得編輯權限。錯誤：{e}")
        return None

def main():
    # 移除側邊欄標題，並使用簡潔的選項標籤
    mode = st.sidebar.radio("請選擇頁面", ["首頁", "管理者頁面"])

    # 使用 session_state 來儲存登入狀態
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False

    if mode == "首頁":
        st.title("會員點數排行榜 🏆")
        
        # 新增重新整理按鈕
        if st.button("重新整理"):
            st.rerun()

        st.info("所有會員點數排名，會即時更新喔！")
        
        sheet = get_sheet_data()
        if sheet:
            data = sheet.get_all_records()
            if data:
                df = pd.DataFrame(data)
                
                # 確保 '點數' 欄位是數字類型，以便正確排序
                df['點數'] = pd.to_numeric(df['點數'])
                
                # 按點數降序排列，並重設索引
                sorted_df = df.sort_values(by='點數', ascending=False).reset_index(drop=True)
                
                st.markdown("---")
                st.subheader("點數冠軍榜 ✨")
                # 視覺化前三名
                if len(sorted_df) >= 3:
                    top_3_cols = st.columns(3)
                    with top_3_cols[0]:
                        st.markdown(f"**🥇 No.1**")
                        st.metric(sorted_df.iloc[0]['暱稱'], value=sorted_df.iloc[0]['點數'])
                    with top_3_cols[1]:
                        st.markdown(f"**🥈 No.2**")
                        st.metric(sorted_df.iloc[1]['暱稱'], value=sorted_df.iloc[1]['點數'])
                    with top_3_cols[2]:
                        st.markdown(f"**🥉 No.3**")
                        st.metric(sorted_df.iloc[2]['暱稱'], value=sorted_df.iloc[2]['點數'])
                elif len(sorted_df) > 0:
                    st.warning("會員人數不足3位，無法顯示完整前三名。")
                
                st.markdown("---")
                st.subheader("完整排行榜")
                
                # 新增一個 '排名' 欄位，從 1 開始編號，並加上 'No.' 前綴
                sorted_df.insert(0, '排名', ['No.' + str(i) for i in range(1, 1 + len(sorted_df))])
                
                # 顯示排名表，並隱藏預設索引
                st.dataframe(sorted_df, hide_index=True)
            else:
                st.warning("目前沒有任何會員資料可顯示。")
    
    elif mode == "管理者頁面":
        if not st.session_state.logged_in:
            # 顯示登入表單
            with st.form(key="admin_login_form"):
                st.subheader("管理者登入 🔐")
                password = st.text_input("輸入密碼", type="password")
                login_button = st.form_submit_button("登入")

            if login_button:
                if password == st.secrets.get("admin_password"):
                    st.session_state.logged_in = True
                    st.success("登入成功！")
                    st.rerun()
                else:
                    st.error("密碼錯誤。")
        else:
            # 登入成功後顯示的管理介面
            st.title("會員管理控制台 ⚙️")
            
            # 使用 st.tabs 建立分頁
            tab1, tab2 = st.tabs(["點數管理", "新增會員"])
            
            # 區塊一：點數管理
            with tab1:
                st.markdown("---")
                st.subheader("會員點數管理")
                
                # 新增重新整理按鈕，並加上唯一的 key
                if st.button("重新整理", key="refresh_admin"):
                    st.rerun()

                sheet = get_sheet_data()
                if sheet:
                    data = sheet.get_all_records()
                    if data:
                        df = pd.DataFrame(data)
                        
                        st.markdown("#### 所有會員列表")
                        st.dataframe(df)
                        
                        # 讓管理員選擇要管理的會員
                        member_nickname = st.selectbox(
                            "選擇要管理的會員暱稱：",
                            options=df['暱稱'].tolist()
                        )
                        
                        if member_nickname:
                            member_data = df[df['暱稱'] == member_nickname].iloc[0]
                            
                            # 使用 st.metric 顯示目前點數，視覺效果更好
                            st.markdown("---")
                            st.subheader(f"會員 {member_nickname} 的點數")
                            st.metric(label="目前點數", value=member_data['點數'])
                            
                            with st.form(key="points_form"):
                                points_change = st.number_input(
                                    "輸入要增減的點數：",
                                    value=0,
                                    step=1
                                )
                                submit_points = st.form_submit_button("更新點數")
                            
                            if submit_points:
                                new_points = int(member_data['點數']) + points_change
                                if new_points < 0:
                                    st.warning("點數不能為負數，請重新輸入。")
                                else:
                                    try:
                                        # 找到該會員在表格中的行號
                                        row_index = df.index[df['暱稱'] == member_nickname].tolist()[0] + 2
                                        # 更新點數欄位（第2欄）
                                        sheet.update_cell(row_index, 2, new_points)
                                        st.success(f"已將會員 **{member_nickname}** 的點數更新為 **{new_points}**！")
                                    except Exception as e:
                                        st.error(f"更新點數時發生錯誤：{e}")
                    else:
                        st.warning("目前沒有任何會員。")
            
            # 區塊二：新增會員
            with tab2:
                st.markdown("---")
                st.subheader("新增會員 ➕")
                st.info("請填寫您的資訊，以創建會員帳號！")

                with st.form(key="registration_form"):
                    nickname = st.text_input("暱稱")
                    # 初始點數為 0
                    initial_points = 0
                    submit_button = st.form_submit_button("創建會員")

                if submit_button:
                    if not nickname:
                        st.error("暱稱為必填欄位。")
                    else:
                        sheet = get_sheet_data()
                        if sheet:
                            # 檢查暱稱是否已存在
                            existing_nicknames = sheet.col_values(1)
                            if nickname in existing_nicknames:
                                st.warning("此暱稱已被使用，請選擇其他暱稱。")
                            else:
                                sheet.append_row([nickname, initial_points])
                                st.success(f"會員 **{nickname}** 創建成功！初始點數為 {initial_points}。")
                                st.balloons()
            
if __name__ == "__main__":
    main()
