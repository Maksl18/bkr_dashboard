import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Налаштування сторінки
st.set_page_config(page_title=" Інтерактивний дашборд для аналізу та прогнозування кількості звернень громадян у місті Вінниці", layout="wide")

# Завантаження даних
@st.cache_data
def load_data():
    df = pd.read_csv("processed_appeals_data.csv")
    df['Date'] = pd.to_datetime(df['Date'])
    kind_df = pd.read_csv("kind_breakdown.csv")
    org_df = pd.read_csv("org_summary.csv")
    methods_df = pd.read_csv("method_timeseries.csv")
    methods_df['Date'] = pd.to_datetime(methods_df['Date'])
    return df, kind_df, org_df, methods_df

df, kind_df, org_df, methods_df = load_data()

# Динамічне отримання метаданих моделі з файлу
current_model = df['best_model'].iloc[0]
model_mae = df['model_mae'].iloc[0]
model_rmse = df['model_rmse'].iloc[0]
model_r2 = df['model_r2'].iloc[0]
model_mape = df['model_mape'].iloc[0]

# --- SIDEBAR ---
st.sidebar.header("⚙️ Налаштування та Фільтри")

# Пояснення роботи фільтрів
st.sidebar.info("""
**Як працюють фільтри:**
1. **Період аналізу:** Впливає на графік 'Динаміка активності: Історія та Прогноз'. Дозволяє детально розглянути активність за конкретні місяці чи тижні.
2. **Вибір організацій:** Фільтрує кругову діаграму та таблицю 'Детальна статистика по організаціях'. Дозволяє порівняти навантаження між конкретними міськими службами.
3. **Завантажити CSV:** Дозволяє завантажити CSV файл з прогнозовании даними.
""")

# 1. Фільтр дат
min_date = df['Date'].min().to_pydatetime()
max_date = df['Date'].max().to_pydatetime()
date_range = st.sidebar.date_input("Оберіть період аналізу", [min_date, max_date])

# 2. Фільтр організацій
all_orgs = org_df['organizationName'].unique().tolist()
selected_orgs = st.sidebar.multiselect("Порівняти конкретні організації", options=all_orgs, default=[])

# --- ЗАСТОСУВАННЯ ФІЛЬТРІВ ---
mask = (df['Date'].dt.date >= date_range[0]) & (df['Date'].dt.date <= date_range[1])
filtered_df = df[mask]

if selected_orgs:
    filtered_org_df = org_df[org_df['organizationName'].isin(selected_orgs)]
else:
    filtered_org_df = org_df

# --- ГОЛОВНИЙ ЗАГОЛОВОК ---
st.title("🏙️ Інтерактивний дашборд для аналізу та прогнозування кількості звернень громадян у м. Вінниця")
st.markdown(f"**Поточна модель прогнозування:** `{current_model}`")

# Вивід всіх метрик моделі (автоматично з даних)
st.subheader("📊 Показники точності прогнозу")
m_col1, m_col2, m_col3, m_col4 = st.columns(4)
with m_col1:
    st.metric("Коефіцієнт R²", f"{model_r2:.4f}")
with m_col2:
    st.metric("MAE (Сер. помилка)", f"{model_mae:.3f}")
with m_col3:
    st.metric("RMSE (Квадр. помилка)", f"{model_rmse:.3f}")
with m_col4:
    st.metric("MAPE (Відносна %)", f"{model_mape:.2f} %")

st.divider()

# --- ГОЛОВНИЙ ГРАФІК ---
st.subheader("📈 Динаміка активності: Історія та Прогноз")
fig_main = go.Figure()

# Історія
hist_data = filtered_df[filtered_df['data_type'] == 'Historical']
fig_main.add_trace(go.Scatter(x=hist_data['Date'], y=hist_data['appeal_count'],
                             name="Фактичні дані (Історія)", line=dict(color="#2ca02c")))

# Прогноз
forecast_data = df[df['data_type'] == 'Forecast']
fig_main.add_trace(go.Scatter(x=forecast_data['Date'], y=forecast_data['appeal_count'],
                             name=f"Прогноз на 14 днів ({current_model})", 
                             line=dict(color="#d62728", width=3, dash='dash')))

# Довірчий інтервал
fig_main.add_trace(go.Scatter(
    x=forecast_data['Date'].tolist() + forecast_data['Date'].tolist()[::-1],
    y=forecast_data['upper_ci'].tolist() + forecast_data['lower_ci'].tolist()[::-1],
    fill='toself', fillcolor='rgba(214, 39, 40, 0.1)',
    line=dict(color='rgba(255,255,255,0)'), name="Межі RMSE похибки"
))
st.plotly_chart(fig_main, use_container_width=True)

# --- ТАБЛИЦЯ ПРОГНОЗУ (Одразу після графіка) ---
st.subheader("📝 Таблиця числових значень прогнозу")
st.info("Показники очікуваної кількості звернень на наступні 14 днів. Ви можете натиснути на заголовок будь-якої колонки, щоб відсортувати дані за зростанням або спаданням.")
# Форматуємо дату для гарного вигляду
forecast_table = forecast_data[['Date', 'appeal_count', 'lower_ci', 'upper_ci']].copy()
forecast_table['Date'] = forecast_table['Date'].dt.strftime('%Y-%m-%d')
forecast_table.columns = ['Дата', 'Прогноз (к-сть)', 'Мін. межа (-RMSE)', 'Макс. межа (+RMSE)']

st.dataframe(
    forecast_table.style.highlight_max(axis=0, color='#ffcccc')
                        .highlight_min(axis=0, color="#9adda9"), 
    use_container_width=True
)

st.divider()

# # --- НОВИЙ ГРАФІК: ЗАСОБИ ЗВ'ЯЗКУ ---
st.subheader("📞 Способи подачі звернень у часі")
# Фільтруємо методи за датою
methods_mask = (methods_df['Date'].dt.date >= date_range[0]) & (methods_df['Date'].dt.date <= date_range[1])
filtered_methods = methods_df[methods_mask]

fig_methods = px.bar(filtered_methods, x="Date", y="count", color="accrualMethod",
                    title="Розподіл за каналами зв'язку",
                    labels={"count": "Кількість звернень", "accrualMethod": "Метод"},
                    color_discrete_sequence=px.colors.qualitative.Pastel)
st.plotly_chart(fig_methods, use_container_width=True)

st.divider() # Додаємо розділювач для візуального комфорту

# --- НИЖНІЙ РЯД ГРАФІКІВ ---
# 1. Перша секція (Тематика)
st.subheader("📂 Тематика звернень")
# 1. Розрахунок відсотків перед створенням графіка
total_appeals = kind_df['count'].sum()
kind_df['percent'] = (kind_df['count'] / total_appeals * 100).round(2)
# 2. Оновлений виклик px.bar
fig_kind = px.bar(kind_df.head(15), x='count', y='kind', orientation='h',
                 color='count', color_continuous_scale='Blues',
                 custom_data=['percent']) # додаємо дані для підказки
# 3. Налаштування відображення
fig_kind.update_layout(yaxis={'categoryorder':'total ascending'})
# 4. Налаштування самого вікна підказки
fig_kind.update_traces(
    hovertemplate="<b>%{y}</b><br>Кількість: %{x}<br>Частка: %{customdata[0]}%<extra></extra>"
)
st.plotly_chart(fig_kind, use_container_width=True)

st.divider() # Додаємо розділювач для візуального комфорту

# 2. Друга секція (Організації)
st.subheader("🏢 Розподіл навантаження на організації")
fig_pie = px.pie(filtered_org_df.head(10), values='total', names='organizationName',
                hole=0.4, title="Топ-10 організацій за обсягом")
fig_pie.update_traces(
    textposition='inside', 
    textinfo='percent+label',
    hovertemplate="<b>%{label}</b><br>Кількість: %{value}<br>Частка: %{percent}<extra></extra>"
)
st.plotly_chart(fig_pie, use_container_width=True)

# Таблиця ефективності внизу
st.subheader("📋 Детальна статистика по організаціях")
st.markdown("""
У цій таблиці наведено показники навантаження та ефективності роботи міських служб:
- **total** — загальна кількість звернень, що надійшли до організації за обраний період.
- **completion_rate** — коефіцієнт виконання (частка завершених звернень відносно загальної кількості).

*Ви можете натиснути на назву будь-якої колонки для автоматичного сортування списку.*
""")
st.dataframe(
    filtered_org_df[['organizationName', 'total', 'completion_rate']]
    .style.format({'completion_rate': '{:.2%}'}),
    use_container_width=True
)

# Кнопка для завантаження результатів
st.sidebar.download_button(
    label="📥 Завантажити CSV з результатами",
    data=df.to_csv(index=False).encode('utf-8'),
    file_name='vinnitsa_appeals_results.csv',
    mime='text/csv',
)
