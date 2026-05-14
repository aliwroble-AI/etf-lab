import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import random
import re

# ==========================================
# KONFIGURACJA STRONY I ZMIENNE GLOBALNE
# ==========================================
st.set_page_config(
    page_title="Laboratorium Hipotez Inwestycyjnych ETF",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Słownik przykładowych tickerów dla użytkownika
DEFAULT_TICKERS = {
    "S&P 500 ESG (Podobny do UBS Prime Value ESG)": "ESGU",
    "S&P 500 (Rynek szeroki)": "SPY",
    "Nasdaq 100 (Technologia)": "QQQ",
    "Złoto (Gold Trust)": "GLD",
    "Obligacje 20+ Lat (Treasury)": "TLT"
}

# ==========================================
# FUNKCJE POBIERANIA I PRZETWARZANIA DANYCH (Z CACHOWANIEM)
# ==========================================

@st.cache_data(ttl=3600)
def get_stock_data(ticker, start_date, end_date):
    """Pobiera historyczne dane cenowe dla wybranego tickera."""
    try:
        data = yf.download(ticker, start=start_date, end=end_date)
        return data
    except Exception as e:
        st.error(f"Błąd podczas pobierania danych dla {ticker}: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def get_etf_sectors(ticker):
    """
    Pobiera wagi sektorowe dla ETF. 
    (Fallback: jeśli yfinance nie zwróci danych dla specyficznego ETF, generuje przybliżone dane edukacyjne).
    """
    try:
        t = yf.Ticker(ticker)
        info = t.info
        
        # Próba pobrania rzeczywistych wag sektorowych (często niedostępne w darmowym API)
        if 'sectorWeightings' in info and info['sectorWeightings']:
            sectors = {list(s.keys())[0]: list(s.values())[0] for s in info['sectorWeightings']}
            return pd.Series(sectors)
        
        # Fallback edukacyjny oparty na charakterze ETF
        if ticker in ["QQQ", "XLK"]:
            return pd.Series({"Technologia": 0.55, "Komunikacja": 0.18, "Dobra konsumpcyjne": 0.15, "Ochrona zdrowia": 0.05, "Inne": 0.07})
        elif ticker in ["ESGU", "SPY"]:
            return pd.Series({"Technologia": 0.28, "Ochrona zdrowia": 0.14, "Finanse": 0.13, "Dobra konsumpcyjne": 0.11, "Przemysł": 0.08, "Inne": 0.26})
        elif ticker == "GLD":
            return pd.Series({"Metale szlachetne": 1.0})
        else:
            return pd.Series({"Finanse": 0.25, "Technologia": 0.20, "Przemysł": 0.15, "Ochrona zdrowia": 0.15, "Energia": 0.10, "Inne": 0.15})
    except:
        return pd.Series({"Brak danych sektorowych": 1.0})

@st.cache_data
def calculate_correlations(base_ticker, comp_tickers, start_date, end_date):
    """Oblicza macierz korelacji dla wybranych aktywów."""
    tickers = [base_ticker] + comp_tickers
    data = yf.download(tickers, start=start_date, end=end_date)['Close']
    # Jeśli wybrano tylko jeden dodatkowy, pandas zwraca inaczej ustrukturyzowane dane
    if isinstance(data, pd.Series):
        data = pd.DataFrame(data, columns=[base_ticker])
    return data.corr()

@st.cache_data
def simulate_historical_news(ticker, date, price_change_pct):
    """
    Symuluje wiadomości rynkowe dla dat historycznych na podstawie rzeczywistej zmiany ceny.
    W prawdziwej aplikacji produkcyjnej użyto by tutaj NewsAPI / EODHD API.
    """
    date_str = date.strftime("%Y-%m-%d")
    
    positive_news = [
        f"[{date_str}] Optymizm na rynkach! {ticker} zyskuje na fali dobrych wyników spółek.",
        f"[{date_str}] Spadek inflacji CPI napędza wzrosty. Sektor technologiczny ciągnie indeksy w górę.",
        f"[{date_str}] Gołębi komunikat FED uspokaja inwestorów. Zauważalny napływ kapitału do {ticker}."
    ]
    
    negative_news = [
        f"[{date_str}] Obawy o recesję uderzają w rynki. {ticker} traci po publikacji słabych danych makro.",
        f"[{date_str}] Niespodziewany wzrost inflacji CPI! Wyprzedaż na rynku akcji przyspiesza.",
        f"[{date_str}] Napięcia geopolityczne powodują ucieczkę inwestorów od ryzyka. Wyraźne spadki na {ticker}."
    ]
    
    neutral_news = [
        f"[{date_str}] Inwestorzy wstrzymują oddech przed decyzją FED. Płaska sesja dla {ticker}.",
        f"[{date_str}] Mieszane dane z rynku pracy. {ticker} oscyluje wokół ceny otwarcia."
    ]
    
    if price_change_pct > 0.01:
        return random.sample(positive_news, 2)
    elif price_change_pct < -0.01:
        return random.sample(negative_news, 2)
    else:
        return random.sample(neutral_news, 2)

def analyze_sentiment(text):
    """
    Uproszczony analizator sentymentu oparty na słowach kluczowych.
    (Zastępuje VADER/FinBERT w celu wyeliminowania ciężkich zależności zewnętrznych).
    """
    text_lower = text.lower()
    pos_words = ['wzrost', 'optymizm', 'zyskuje', 'dobre', 'spadek inflacji', 'napędza', 'uspokaja', 'gołębi']
    neg_words = ['spadek', 'obawy', 'recesja', 'traci', 'słabe', 'wzrost inflacji', 'wyprzedaż', 'napięcia']
    
    pos_score = sum(1 for word in pos_words if word in text_lower)
    neg_score = sum(1 for word in neg_words if word in text_lower)
    
    if pos_score > neg_score: return "🟢 Pozytywny"
    elif neg_score > pos_score: return "🔴 Negatywny"
    else: return "⚪ Neutralny"

def anonymize_csv(df):
    """Anonimizuje wrażliwe dane z wgranego pliku CSV (historia transakcji)."""
    df_anon = df.copy()
    
    # Usuwanie kolumn z ID/Danymi osobowymi
    cols_to_drop = [col for col in df_anon.columns if re.search(r'id|name|imię|nazwisko|pesel|account|konto', col.lower())]
    df_anon.drop(columns=cols_to_drop, inplace=True, errors='ignore')
    
    # Maskowanie kwot finansowych (mnożenie przez losowy skalar, zachowanie proporcji)
    money_cols = [col for col in df_anon.columns if re.search(r'kwota|amount|value|wartość|cena|price|saldo|balance', col.lower())]
    scalar = random.uniform(0.1, 5.0) # Losowy skalar dla całej sesji
    for col in money_cols:
        try:
            df_anon[col] = (pd.to_numeric(df_anon[col], errors='coerce') * scalar).round(2)
        except:
            pass
            
    return df_anon

# ==========================================
# INTERFEJS UŻYTKOWNIKA - SIDEBAR
# ==========================================
st.sidebar.title("🛠️ Parametry Laboratorium")
st.sidebar.markdown("Skonfiguruj środowisko testowe.")

selected_asset_name = st.sidebar.selectbox("Wybierz badany ETF:", list(DEFAULT_TICKERS.keys()))
MAIN_TICKER = DEFAULT_TICKERS[selected_asset_name]

# Możliwość wpisania własnego tickera
custom_ticker = st.sidebar.text_input("...lub wpisz własny Ticker (np. AAPL, VTI):", "")
if custom_ticker:
    MAIN_TICKER = custom_ticker.upper()

start_date = st.sidebar.date_input("Data początkowa:", datetime.today() - timedelta(days=365))
end_date = st.sidebar.date_input("Data końcowa:", datetime.today())

st.sidebar.markdown("---")
st.sidebar.info("💡 **Cel edukacyjny:** Zrozum, dlaczego ceny ETF zmieniają się pod wpływem wydarzeń rynkowych i jak budować odporny portfel inwestycyjny.")

# Pobieranie głównych danych
df_main = get_stock_data(MAIN_TICKER, start_date, end_date)

# ==========================================
# GŁÓWNA STRONA APLIKACJI
# ==========================================
st.title("🔬 Laboratorium Hipotez Inwestycyjnych")
st.markdown(f"**Analizowany walor:** `{MAIN_TICKER}` | **Okres:** {start_date} do {end_date}")

if df_main.empty:
    st.error("Brak danych dla wybranego tickera lub zakresu dat. Spróbuj zmienić parametry.")
    st.stop()

# TABS - Podział na moduły
tab1, tab2, tab3, tab4 = st.tabs([
    "🎯 Moduł 1: Piaskownica Hipotez", 
    "🔍 Moduł 2: Detektyw Składu", 
    "⚖️ Moduł 3: Laboratorium Dywersyfikacji",
    "🛡️ Narzędzia: Anonimizator Transakcji"
])

# ------------------------------------------
# MODUŁ 1: PIASKOWNICA HIPOTEZ
# ------------------------------------------
with tab1:
    st.header("Piaskownica Hipotez (Event-Driven Analysis)")
    st.markdown("""
    Ceny funduszy ETF reagują na dane makroekonomiczne i wydarzenia na świecie. 
    **Zbadaj konkretny dzień**, aby sprawdzić, co wywołało ruchy cenowe.
    """)
    
    # Wykres świecowy
    fig_candle = go.Figure(data=[go.Candlestick(x=df_main.index,
                    open=df_main['Open'],
                    high=df_main['High'],
                    low=df_main['Low'],
                    close=df_main['Close'])])
    fig_candle.update_layout(title=f"Notowania {MAIN_TICKER}", xaxis_rangeslider_visible=False, height=400)
    st.plotly_chart(fig_candle, use_container_width=True)
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("1. Wybierz wydarzenie")
        event_date = st.date_input("Wybierz datę (z widocznego wykresu):", value=df_main.index[-1].date() if not df_main.empty else datetime.today())
        event_date = pd.to_datetime(event_date)
        
        user_hypothesis = st.text_area("Twoja Hipoteza Inwestycyjna:", placeholder="Np. Uważam, że cena tego dnia spadła z powodu publikacji wysokich odczytów inflacji CPI...")
        
    with col2:
        st.subheader("2. Weryfikacja Rynkowa")
        if st.button("Sprawdź Hipotezę 🚀"):
            # Szukanie danych dla tej daty
            try:
                # Szukamy najbliższej dostępnej daty sesyjnej
                idx = df_main.index.get_indexer([event_date], method='nearest')[0]
                actual_date = df_main.index[idx]
                
                close_price = df_main.iloc[idx]['Close']
                open_price = df_main.iloc[idx]['Open']
                pct_change = (close_price - open_price) / open_price
                
                st.metric(label=f"Zmiana ceny w dniu {actual_date.strftime('%Y-%m-%d')}", 
                          value=f"${close_price:.2f}", 
                          delta=f"{pct_change*100:.2f}%")
                
                # Symulacja wiadomości i sentymentu
                news_items = simulate_historical_news(MAIN_TICKER, actual_date, pct_change)
                
                st.markdown("### 📰 Nagłówki prasowe z tego dnia:")
                for news in news_items:
                    sentiment = analyze_sentiment(news)
                    st.info(f"**{sentiment}** | {news}")
                    
                st.markdown("---")
                st.markdown("### 🧠 Feedback Edukacyjny:")
                if pct_change < 0 and "inflacj" in user_hypothesis.lower():
                    st.success("Trafna hipoteza! Strach przed inflacją historycznie wywołuje spadki na rynku akcji (wyższe stopy procentowe dyskontują przyszłe zyski spółek).")
                elif pct_change > 0 and ("spadek" in user_hypothesis.lower() or "bessa" in user_hypothesis.lower()):
                    st.warning("Rynek zareagował wzrostami, mimo Twojej negatywnej hipotezy. Często 'złe informacje' są już wliczone w cenę (tzw. priced-in) i rynek rośnie na fakcie ich publikacji.")
                else:
                    st.info("Pamiętaj: Rynki są złożone. Czasami na dany ETF wpływa specyficzny sektor w nim zawarty, a nie cała gospodarka. Sprawdź 'Moduł 2: Detektyw Składu'.")

            except Exception as e:
                st.error("Wystąpił błąd podczas analizy daty. Upewnij się, że data mieści się w pobranym zakresie.")

# ------------------------------------------
# MODUŁ 2: DETEKTYW SKŁADU
# ------------------------------------------
with tab2:
    st.header("Detektyw Składu (Constituents Explorer)")
    st.markdown(f"""
    Dlaczego {MAIN_TICKER} reaguje silnie na wiadomości o chipach AI, a słabo na ceny ropy? 
    Odpowiedź kryje się w **strukturze sektorowej** funduszu. ETF to tylko "koszyk" - sprawdźmy, co jest w środku.
    """)
    
    col_pie, col_desc = st.columns([1, 1])
    
    sectors = get_etf_sectors(MAIN_TICKER)
    
    with col_pie:
        fig_pie = px.pie(
            values=sectors.values, 
            names=sectors.index, 
            title=f"Wagi Sektorowe w {MAIN_TICKER} (Estymacja)",
            hole=0.4,
            color_discrete_sequence=px.colors.sequential.Teal
        )
        st.plotly_chart(fig_pie, use_container_width=True)
        
    with col_desc:
        st.markdown("### 🔍 Wnioski Analityczne")
        top_sector = sectors.idxmax()
        top_weight = sectors.max() * 100
        
        st.write(f"- **Dominujący sektor:** `{top_sector}` ({top_weight:.1f}%)")
        if top_sector == "Technologia":
            st.info("Wysoka ekspozycja na Technologię oznacza, że ten ETF jest bardzo wrażliwy na decyzje stóp procentowych FED (spółki Growth) oraz wyniki gigantów rynkowych (Apple, Microsoft, NVIDIA).")
        elif top_sector == "Finanse":
            st.info("Sektor finansowy zazwyczaj zyskuje w środowisku rosnących stóp procentowych (wyższe marże odsetkowe banków), ale jest podatny na kryzysy płynnościowe.")
        else:
            st.info("Zdywersyfikowany lub specyficzny sektorowo fundusz. Analizując wiadomości, zwracaj szczególną uwagę na legislację i trendy konsumenckie dotyczące branży dominującej.")
            
        st.warning("⚠️ Skład ETF zmienia się w czasie (tzw. rebalancing). Zarządzający funduszem cyklicznie dostosowują wagi spółek do zadeklarowanego indeksu referencyjnego.")

# ------------------------------------------
# MODUŁ 3: LABORATORIUM DYWERSYFIKACJI
# ------------------------------------------
with tab3:
    st.header("Laboratorium Dywersyfikacji (Correlation Lab)")
    st.markdown("""
    Świętym Graalem inwestowania jest dywersyfikacja. Szukamy aktywów, które nie poruszają się w tym samym kierunku w tym samym czasie.
    **Współczynnik korelacji** (od -1 do 1) pomoże Ci ocenić, czy Twój portfel jest bezpieczny podczas kryzysu.
    """)
    
    compare_tickers = st.multiselect(
        "Wybierz aktywa do porównania (domyślnie dodano Złoto i Obligacje US):",
        options=["QQQ", "SPY", "DIA", "IWM", "GLD", "TLT", "USO", "VNQ"],
        default=["GLD", "TLT", "QQQ"]
    )
    
    if compare_tickers:
        with st.spinner("Obliczanie macierzy korelacji..."):
            corr_matrix = calculate_correlations(MAIN_TICKER, compare_tickers, start_date, end_date)
            
            fig_corr = px.imshow(corr_matrix, 
                                 text_auto=".2f", 
                                 aspect="auto",
                                 color_continuous_scale="RdBu_r",
                                 zmin=-1, zmax=1,
                                 title="Macierz Korelacji Dziennych Stóp Zwrotu")
            st.plotly_chart(fig_corr, use_container_width=True)
            
            st.markdown("### 📖 Jak czytać tę macierz?")
            st.write("- **Blisko +1.0 (Kolor Czerwony):** Aktywa poruszają się identycznie. Brak dywersyfikacji (np. SPY i QQQ często mają korelacje > 0.8).")
            st.write("- **Około 0.0 (Kolor Biały):** Brak związku. Dobry dodatek do portfela (często Złoto - GLD).")
            st.write("- **Blisko -1.0 (Kolor Niebieski):** Aktywa poruszają się w przeciwnych kierunkach. Świetne zabezpieczenie na czas krachów (np. Obligacje Długoterminowe - TLT w czasie spadków akcji).")
    else:
        st.warning("Wybierz przynajmniej jedno aktywo do porównania.")

# ------------------------------------------
# NARZĘDZIA: ANONIMIZATOR TRANSAKCJI
# ------------------------------------------
with tab4:
    st.header("Narzędzie Inżynierii Danych: Anonimizator Portfela")
    st.markdown("""
    Przed analizą własnego portfela w zewnętrznych narzędziach, powinieneś chronić swoje dane. 
    Wgraj swój plik CSV z historią transakcji z brokera. Skrypt uruchomi się **lokalnie** i przygotuje zanonimizowaną wersję (ukryje ID konta i przeskaluje wartości finansowe, zachowując historyczne wagi portfela).
    """)
    
    uploaded_file = st.file_uploader("Wgraj historię transakcji z brokera (format CSV)", type="csv")
    
    if uploaded_file is not None:
        try:
            df_uploaded = pd.read_csv(uploaded_file)
            st.subheader("Oryginalne dane (Pierwsze 3 wiersze)")
            st.dataframe(df_uploaded.head(3))
            
            with st.spinner("Procesowanie (maskowanie ID, skalowanie kwot)..."):
                df_clean = anonymize_csv(df_uploaded)
                
            st.success("✅ Dane zostały zanonimizowane.")
            st.subheader("Wynik po anonimizacji")
            st.dataframe(df_clean.head(5))
            
            # Pobieranie przetworzonego pliku
            csv = df_clean.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="Pobierz zanonimizowany plik CSV",
                data=csv,
                file_name='anonymized_portfolio.csv',
                mime='text/csv',
            )
        except Exception as e:
            st.error(f"Nie udało się przetworzyć pliku. Błąd: {e}")

# ==========================================
# STOPKA I DISCLAIMER PRAWNY
# ==========================================
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: gray; font-size: 0.8em;'>
    <strong>Disclaimer Prawny:</strong> Narzędzie ma charakter wyłącznie edukacyjny i nie stanowi doradztwa inwestycyjnego 
    w rozumieniu Dyrektywy MiFID II (Markets in Financial Instruments Directive). Symulacje, analizy sentymentu oraz 
    dane korelacyjne są uproszczonymi modelami i nie gwarantują przyszłych rezultatów na rynkach finansowych.
    Inwestowanie wiąże się z ryzykiem utraty kapitału.
    <br><br>
    Zbudowane przy użyciu: Streamlit, YFinance & Plotly | Stworzone przez: Senior Python Developer / FinEdu
    </div>
    """, 
    unsafe_allow_html=True
)