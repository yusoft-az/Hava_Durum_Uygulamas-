// script.js
document.addEventListener('DOMContentLoaded', () => {
    // Element Referansları
    const cityInput = document.getElementById('city-input');
    const searchButton = document.getElementById('search-button');
    const suggestionsList = document.getElementById('suggestions-list'); // <<< Yeni
    const cityNameElement = document.getElementById('city-name');
    const currentTempElement = document.getElementById('current-temp');
    const currentIconElement = document.getElementById('current-icon');
    const currentDescElement = document.getElementById('current-desc');
    const minMaxTempElement = document.getElementById('min-max-temp');
    const hourlyItemsContainer = document.getElementById('hourly-items-container');
    const dailyItemsContainer = document.getElementById('daily-items-container');
    const errorMessageElement = document.getElementById('error-message');
    const currentInfoArea = document.getElementById('current-info-area');
    const hourlyBlock = document.getElementById('hourly-forecast-block');
    const dailyBlock = document.getElementById('daily-forecast-block');

    // API ve Zamanlama Değişkenleri
    const API_BASE_URL = "http://localhost:5000";
    let suggestionDebounceTimer;
    const DEBOUNCE_DELAY = 350; // ms

    // Arka plan resmi base yolu (backend'den gelen dosya adıyla birleştirilecek)
    const BG_BASE_PATH = "assets/gifs/"; // <<< index.html'e göre path

    // --- Ana Hava Durumu Fonksiyonu ---
    async function fetchWeather(city, country = '') { // Ülke kodu da alabilir
        hideError();
        showLoadingPlaceholders();
        suggestionsList.style.display = 'none'; // Önerileri gizle

        try {
            const url = `${API_BASE_URL}/weather?city=${encodeURIComponent(city)}` + (country ? `&country=${encodeURIComponent(country)}` : '');
            const response = await fetch(url);
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ message: `Hata (${response.status})` }));
                throw new Error(errorData.message || `HTTP ${response.status}`);
            }
            const data = await response.json();
            if (data.success) updateUI(data);
            else throw new Error(data.message || "Bilinmeyen API hatası.");
        } catch (error) {
            console.error("Hava durumu alınırken hata:", error);
            showError(error.message);
            clearUI();
        }
    }

    // --- Arayüz Güncelleme ---
    function updateUI(data) {
        // 1. Arka Planı Güncelle (Backend'den gelen dosya adıyla)
        const bgImageName = data.current.background_image || "1.jpg"; // Varsayılan
        document.body.style.backgroundImage = `url('${BG_BASE_PATH}${bgImageName}')`;

        // 2. Ana Bilgileri Güncelle (Backend'den gelen tam şehir adını kullan)
        cityNameElement.textContent = `${data.city.name}, ${data.city.country}`;
        currentTempElement.textContent = data.current.temp !== null ? `${Math.round(data.current.temp)}°` : '--°';
        currentDescElement.textContent = data.current.desc || '---';
        minMaxTempElement.textContent = (data.current.temp_min !== null && data.current.temp_max !== null)
            ? `D: ${Math.round(data.current.temp_min)}°   Y: ${Math.round(data.current.temp_max)}°`
            : 'D: --°   Y: --°';
        if (data.current.icon) {
            currentIconElement.src = `http://openweathermap.org/img/wn/${data.current.icon}@2x.png`;
            currentIconElement.style.display = 'block'; currentIconElement.alt = data.current.desc;
        } else { currentIconElement.style.display = 'none'; }
        currentInfoArea.style.display = 'block'; hourlyBlock.style.display = 'block'; dailyBlock.style.display = 'block';

        // 3. Saatlik Tahmini Güncelle
        hourlyItemsContainer.innerHTML = '';
        if (data.hourly && data.hourly.length > 0) { /* ... (içerik aynı) ... */
            data.hourly.forEach(hour => {
                const itemDiv = document.createElement('div'); itemDiv.classList.add('hourly-item');
                const timeSpan = document.createElement('span'); timeSpan.classList.add('time'); timeSpan.textContent = hour.time;
                const iconImg = document.createElement('img'); iconImg.src = `http://openweathermap.org/img/wn/${hour.icon}@2x.png`; iconImg.alt = '';
                const tempSpan = document.createElement('span'); tempSpan.classList.add('temp'); tempSpan.textContent = hour.temp !== null ? `${Math.round(hour.temp)}°` : '--°';
                itemDiv.appendChild(timeSpan); itemDiv.appendChild(iconImg); itemDiv.appendChild(tempSpan); hourlyItemsContainer.appendChild(itemDiv);
            });
        } else { hourlyItemsContainer.innerHTML = '<div class="loading-placeholder">Saatlik veri yok</div>'; }

        // 4. Günlük Tahmini Güncelle
        dailyItemsContainer.innerHTML = '';
        if (data.daily && data.daily.length > 0) { /* ... (içerik aynı) ... */
            data.daily.forEach(day => {
                const itemDiv = document.createElement('div'); itemDiv.classList.add('daily-item');
                const daySpan = document.createElement('span'); daySpan.classList.add('day'); daySpan.textContent = day.day;
                const iconImg = document.createElement('img'); iconImg.src = `http://openweathermap.org/img/wn/${day.icon}@2x.png`; iconImg.alt = '';
                const minSpan = document.createElement('span'); minSpan.classList.add('temp-min'); minSpan.textContent = day.temp_min !== null ? `${Math.round(day.temp_min)}°` : '--°';
                const maxSpan = document.createElement('span'); maxSpan.classList.add('temp-max'); maxSpan.textContent = day.temp_max !== null ? `${Math.round(day.temp_max)}°` : '--°';
                itemDiv.appendChild(daySpan); itemDiv.appendChild(iconImg); itemDiv.appendChild(minSpan); itemDiv.appendChild(maxSpan); dailyItemsContainer.appendChild(itemDiv);
            });
        } else { dailyItemsContainer.innerHTML = '<div class="loading-placeholder">Günlük veri yok</div>'; }
    }

    // --- Şehir Önerileri Fonksiyonları ---
    async function fetchSuggestions(query) {
        if (query.length < 2) { // En az 2 karakter
            suggestionsList.innerHTML = '';
            suggestionsList.style.display = 'none';
            return;
        }
        try {
            const response = await fetch(`${API_BASE_URL}/suggestions?q=${encodeURIComponent(query)}`);
            if (!response.ok) throw new Error('Öneri alınamadı');
            const suggestions = await response.json();
            displaySuggestions(suggestions);
        } catch (error) {
            console.error("Öneri hatası:", error);
            suggestionsList.innerHTML = '';
            suggestionsList.style.display = 'none';
        }
    }

    function displaySuggestions(suggestions) {
        suggestionsList.innerHTML = ''; // Öncekileri temizle
        if (suggestions.length === 0) {
            suggestionsList.style.display = 'none';
            return;
        }
        suggestions.forEach(suggestion => {
            const itemDiv = document.createElement('div');
            itemDiv.classList.add('suggestion-item');
            itemDiv.textContent = suggestion.display; // Gösterilecek isim
            // Tıklama olayını ekle
            itemDiv.addEventListener('click', () => {
                cityInput.value = suggestion.display; // Input'u güncelle
                suggestionsList.innerHTML = ''; // Listeyi temizle
                suggestionsList.style.display = 'none'; // Listeyi gizle
                // Hava durumunu bu seçilen şehir için getir (isim ve ülke kodu ile)
                fetchWeather(suggestion.name, suggestion.country);
            });
            suggestionsList.appendChild(itemDiv);
        });
        suggestionsList.style.display = 'block'; // Listeyi göster
    }

    // Debounce fonksiyonu
    function debounce(func, delay) {
        clearTimeout(suggestionDebounceTimer);
        suggestionDebounceTimer = setTimeout(func, delay);
    }

    // --- Yardımcı Fonksiyonlar (Hata, Temizleme, Yükleme) ---
    function showError(message) { errorMessageElement.textContent = message; errorMessageElement.style.display = 'block'; }
    function hideError() { errorMessageElement.textContent = ''; errorMessageElement.style.display = 'none'; }
    function clearUI() { cityNameElement.textContent = '--'; currentTempElement.textContent = '--°'; currentIconElement.style.display = 'none'; currentDescElement.textContent = '---'; minMaxTempElement.textContent = 'D: --° Y: --°'; hourlyItemsContainer.innerHTML = ''; dailyItemsContainer.innerHTML = ''; document.body.style.backgroundImage = `url('${BG_BASE_PATH}${DEFAULT_BG_IMAGE_NAME}')`; } // Varsayılan resme dön
    function showLoadingPlaceholders() { hourlyItemsContainer.innerHTML = '<div class="loading-placeholder">Yükleniyor...</div>'; dailyItemsContainer.innerHTML = '<div class="loading-placeholder">Yükleniyor...</div>'; }

    // --- Olay Dinleyicileri ---
    searchButton.addEventListener('click', () => {
        const city = cityInput.value.trim();
        if (city) fetchWeather(city);
        else showError("Lütfen bir şehir adı girin.");
        suggestionsList.style.display = 'none'; // Aramadan sonra önerileri gizle
    });

    cityInput.addEventListener('keypress', (event) => { if (event.key === 'Enter') searchButton.click(); });

    // <<< YENİ: Şehir Input'una Yazma Olayı (Debounce ile) >>>
    cityInput.addEventListener('input', () => {
        const query = cityInput.value.trim();
        debounce(() => fetchSuggestions(query), DEBOUNCE_DELAY);
    });

    // <<< YENİ: Önerileri Gizlemek İçin Odak Kaybı ve Tıklama >>>
    cityInput.addEventListener('blur', () => {
        // Tıklamaya izin vermek için küçük bir gecikme
        setTimeout(() => {
            // Eğer fare hala öneri listesi üzerindeyse gizleme
             if (!suggestionsList.matches(':hover')) {
                  suggestionsList.style.display = 'none';
             }
        }, 200); // 200ms gecikme
    });
    // Başka bir yere tıklayınca da gizle (daha genel)
    document.addEventListener('click', (event) => {
        if (!cityInput.contains(event.target) && !suggestionsList.contains(event.target)) {
             suggestionsList.style.display = 'none';
        }
    });


    // Başlangıçta varsayılan şehir için veriyi yükle
    fetchWeather("İstanbul");

});