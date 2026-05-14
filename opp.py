import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px

# --- KONFIGURACJA STRONY ---
st.set_page_config(page_title="Laboratorium Cykli Rynkowych", layout="wide")

# --- WARSTWA DANYCH I OBSŁUGA BŁĘDÓW (FALLBACK) ---
@st.cache_data(ttl=3600)
def fetch_data(tickers, start, end, regime="neutral"):
    """
    Pobiera dane z yfinance. W przypadku błędu API generuje syntetyczne dane edukacyjne (mock data),
    odzwierciedlające specyfikę danego reżimu rynkowego, aby aplikacja działała bez przerw.
    """
    try:
        df = yf.download(tickers, start=start, end=end, progress=False)['Close']
        if df.empty or df.isnull().all().all():
            raise ValueError("Brak danych z API")
        if isinstance(df, pd.Series):
            df = df.to_frame(name=tickers)
        return df.dropna()
    except Exception:
        st.warning("⚠️ Niestabilność zewnętrznego API yfinance. Uruchomiono tryb symulacji edukacyjnej (dane syntetyczne).")
        dates = pd.date_range(start, end, freq='B')
        np.random.seed(42)
        mock_data = pd.DataFrame(index=dates)
        
        # Symulacja stóp zwrotu w zależności od reżimu (uproszczony model czynnikowy)
        market_factor = np.random.normal(0, 0.01, len(dates))
        inflation_factor = np.random.normal(0, 0.01, len(dates))
        
        for ticker in tickers:
            if ticker in or ticker.startswith('XL'):
                if regime == "inflation":
                    returns = market_factor - inflation_factor * 1.5 + np.random.normal(0, 0.005, len(dates))
                elif regime == "ai_boom" and ticker == 'QQQ':
                    returns = market_factor + 0.002 + np.random.normal(0, 0.015, len(dates))
                else:
                    returns = market_factor + np.random.normal(0, 0.005, len(dates))
            elif ticker == 'TLT':
                if regime == "inflation":
                    returns = -inflation_factor * 2.0 + np.random.normal(0, 0.002, len(dates)) # Dodatnia korelacja z SPY (oba spadają)
                else:
                    returns = -market_factor * 0.5 + np.random.normal(0, 0.002, len(dates)) # Ujemna korelacja z SPY
            elif ticker == 'GLD':
                returns = inflation_factor * 1.2 + np.random.normal(0, 0.008, len(dates))
            else:
                returns = np.random.normal(0.0002, 0.01, len(dates))
                
            mock_data[ticker] = 100 * np.exp(np.cumsum(returns))
            
        return mock_data

# --- NAWIGACJA (SIDEBAR) ---
st.sidebar.title("Nawigacja")
st.sidebar.markdown("Wybierz moduł analityczny:")
modul = st.sidebar.radio("Wybierz:",)

# --- MODUŁ 1: ANATOMIA KRYZYSÓW ---
if modul == "1. Anatomia Kryzysów i Przełomów":
    st.title("Anatomia Kryzysów i Przełomów")
    st.markdown("Wybierz historyczne zjawisko makroekonomiczne, aby przeanalizować mechanikę przepływu kapitału.")
    
    event = st.selectbox("Wydarzenie Makroekonomiczne:",)
    
    if "Szok Inflacyjny" in event:
        start_date, end_date = "2021-06-01", "2023-06-01"
        regime = "inflation"
        st.subheader("Kontekst: Rozgrzana gospodarka i przerwane łańcuchy dostaw")
        st.markdown("Potężna stymulacja fiskalna zderzyła się z ograniczoną podażą. Inflacja, początkowo ignorowana, zaczęła narastać miesiącami, zakorzeniając się w gospodarce.")
        st.subheader("Iskra: Wojna i odczyty CPI > 8%")
        st.markdown("Szok energetyczny z początku 2022 r. zmusił bank centralny (FED) do panicznego, najszybszego od dekad cyklu podnoszenia stóp procentowych.")
        st.subheader("Skutek: Załamanie wycen obligacji i akcji")
        st.markdown("Wysokie stopy zdewastowały obligacje długoterminowe (TLT) i obniżyły wyceny rynków akcji (SPY). Złoto (GLD) początkowo cierpiało przez silnego dolara.")
    elif "Wybuch Pandemii" in event:
        start_date, end_date = "2020-01-01", "2020-12-31"
        regime = "neutral"
        st.subheader("Kontekst: Późny cykl ekspansji i niskiej zmienności")
        st.markdown("Rynki znajdowały się w długiej fazie spokojnego wzrostu przy historycznie niskiej zmienności. Powszechnie zakładano nieprzerwaną ciągłość procesów biznesowych.")
        st.subheader("Iskra: Globalny Lockdown")
        st.markdown("Fizyczne zamrożenie gospodarek z dnia na dzień wywołało brutalny kryzys płynnościowy. Kapitał w panice uciekał z każdego aktywa ryzykownego.")
        st.subheader("Skutek: Tarcza z Obligacji i Hossa Technologiczna")
        st.markdown("Agresywne obcięcie stóp do zera i dodruk kapitału wystrzeliły wyceny obligacji (TLT). Sektor technologiczny (QQQ) błyskawicznie stał się beneficjentem przymusowej cyfryzacji.")
    else:
        start_date, end_date = "2023-01-01", "2024-06-01"
        regime = "ai_boom"
        st.subheader("Kontekst: Koszt kapitału i ciche zbrojenia technologiczne")
        st.markdown("Mimo restrykcyjnej polityki monetarnej, giganci technologiczni intensywnie inwestowali w chmurę i wielkie modele językowe z dala od głównego nurtu uwag rynków.")
        st.subheader("Iskra: Raporty finansowe NVIDIA")
        st.markdown("Twarde dowody w postaci rewelacyjnych wyników i prognoz producentów układów scalonych (GPU) w połowie 2023 r. udowodniły istnienie strukturalnego popytu.")
        st.subheader("Skutek: Ekstremalna Dywergencja")
        st.markdown("Podczas gdy szeroki rynek (SPY) walczył z wysokimi stopami, a obligacje (TLT) szorowały po dnie, wskaźnik QQQ całkowicie zignorował grawitację makroekonomiczną.")

    tickers =
    data = fetch_data(tickers, start_date, end_date, regime)
    
    # Normalizacja bazy (pierwszy punkt = 100)
    normalized_data = (data / data.iloc) * 100
    
    fig = px.line(normalized_data, x=normalized_data.index, y=tickers, 
                  labels={'value': 'Znormalizowana Stopa Zwrotu (Baza=100)', 'index': 'Data', 'variable': 'Aktywo'},
                  title=f"Wyceny Głównych Klas Aktywów ({start_date} do {end_date})")
    st.plotly_chart(fig, use_container_width=True)

# --- MODUŁ 2: RENTGEN SEKTORÓW ---
elif modul == "2. Rentgen Sektorów":
    st.title("Rentgen Sektorów (Rotacja Kapitału)")
    st.markdown("Zobacz, w jaki sposób różne fazy makroekonomiczne faworyzują odmienne sektory gospodarki.")
    
    okres = st.selectbox("Wybierz reżim rynkowy:",)
    
    if "Szok Inflacyjny" in okres:
        start_date, end_date = "2022-01-01", "2022-12-31"
        st.info("**Logika Makro:** W środowisku drastycznie rosnących stóp procentowych i inflacji, technologiczne spółki wzrostowe (XLK) cierpią przez wysoką stopę dyskontową. Zyskują sektory surowcowe i energetyczne (XLE), chroniące przed utratą siły nabywczej pieniądza.")
    else:
        start_date, end_date = "2020-04-01", "2021-04-01"
        st.info("**Logika Makro:** Przy stopach procentowych bliskich zera i potężnej stymulacji gospodarki popyt eksploduje. Technologie (XLK) rosną na cyfryzacji, zyskują dobra dyskrecjonalne, a sektory defensywne jak usługi komunalne (XLU) odstają od rynkowego rajdu.")

    sectors =
    data = fetch_data(sectors, start_date, end_date)
    
    # Obliczenie stopy zwrotu w podanym okresie
    returns = ((data.iloc[-1] - data.iloc) / data.iloc) * 100
    returns_df = returns.reset_index()
    returns_df.columns =
    returns_df = returns_df.sort_values(by='Stopa Zwrotu (%)', ascending=False)
    
    fig = px.bar(returns_df, x='Sektor', y='Stopa Zwrotu (%)', color='Stopa Zwrotu (%)',
                 color_continuous_scale='RdYlGn', text='Stopa Zwrotu (%)',
                 title=f"Stopy zwrotu głównych ETF-ów sektorowych ({start_date} do {end_date})")
    fig.update_traces(texttemplate='%{text:.2f}%', textposition='outside')
    st.plotly_chart(fig, use_container_width=True)

# --- MODUŁ 3: SKANER ZMIENNYCH KORELACJI ---
elif modul == "3. Skaner Zmiennych Korelacji":
    st.title("Skaner Zmiennych Korelacji")
    st.markdown("Dywersyfikacja to nie stała wartość fizyczna. Zobacz jak środowisko inflacyjne niszczy klasyczny portfel 60/40.")
    
    regime_korelacji = st.selectbox("Wybierz epokę makroekonomiczną:",)
    
    if "Gospodarka 'Złotowłosej'" in regime_korelacji:
        start_date, end_date = "2015-01-01", "2019-12-31"
        regime = "neutral"
        st.success("**Wyjaśnienie:** W tym okresie rynki bały się wyłącznie o spowolnienie wzrostu, a inflacja praktycznie nie istniała. Kiedy akcje (SPY) spadały, ucieczka do bezpiecznej przystani windowała ceny obligacji (TLT). **Ujemna korelacja ratowała portfele.**")
    else:
        start_date, end_date = "2021-01-01", "2023-12-31"
        regime = "inflation"
        st.error("**Wyjaśnienie:** Powrót potężnej inflacji zmienił wektor kierunkowy korelacji. Agresywne podnoszenie stóp uderzyło równocześnie w wyceny spółek (SPY) i doprowadziło do załamania historycznie przewartościowanych obligacji skarbowych (TLT). **Dywersyfikacja przestała działać (korelacja dodatnia).**")

    tickers =
    data = fetch_data(tickers, start_date, end_date, regime)
    
    # Kalkulacja dziennych stóp zwrotu i korelacji Pearsona
    daily_returns = data.pct_change().dropna()
    correlation_matrix = daily_returns.corr()
    
    fig = px.imshow(correlation_matrix, text_auto=".2f", color_continuous_scale='RdBu_r', 
                    zmin=-1, zmax=1, aspect="auto", 
                    title=f"Macierz Korelacji (Stopy zwrotu {start_date} do {end_date})")
    st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    st.markdown("💡 *Zauważ na mapie cieplnej (heatmap) zmianę koloru pomiędzy przecięciem SPY/QQQ a TLT. Ciemnoniebieski oznacza silną ujemną korelację (ochronę kapitału), a czerwony - dodatnią (spadki na obu frontach).*")
