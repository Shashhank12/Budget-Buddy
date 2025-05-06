const lineChartCategoryImage = document.getElementById('lineChartCategory');
const lineChartCategoryLoadingIndicator = document.getElementById('lineChartCategoryLoading');
const pieChartImage = document.getElementById('pieChartSidebar');
const pieLoadingIndicator = document.getElementById('pieChartLoadingSidebar');
const categoryPieChartImage = document.getElementById('categoryPieChartSidebar');
const categoryPieLoadingIndicator = document.getElementById('categoryPieChartLoadingSidebar');
const predictionChartImage = document.getElementById('predictionChart');
const predictionChartLoadingIndicator = document.getElementById('predictionChartLoading');
const predictionAnalysisTextDiv = document.getElementById('predictionAnalysisText');
const predictionAnalysisLoadingIndicator = document.getElementById('predictionAnalysisLoading');

const viewSelect = document.getElementById('viewSelect');
const prevButton = document.getElementById('prevButton');
const nextButton = document.getElementById('nextButton');
const currentTimeframeSpan = document.getElementById('currentTimeframe');
const hiddenViewInput = document.getElementById('hidden_time_view');
const hiddenOffsetInput = document.getElementById('hidden_time_offset');
const hiddenStartDateInput = document.getElementById('hidden_start_date_form');
const hiddenEndDateInput = document.getElementById('hidden_end_date_form');
const timeframeForm = document.getElementById('timeframeForm');

const chatFab = document.getElementById('chat-fab');
const chatPopup = document.getElementById('chat-popup');
const closeChatPopup = document.getElementById('close-chat-popup');
const chatHistory = document.getElementById('chatHistory');
const chatInput = document.getElementById('chatInput');
const sendChatButton = document.getElementById('sendChatButton');
const chatLoadingIndicator = document.getElementById('chatLoadingIndicator');
const chatPeriodDisplay = document.getElementById('chat-period-display');
const chatSuggestionsContainer = document.querySelector('.chat-suggestions');

let currentView = hiddenViewInput.value || 'month';
let currentOffset = parseInt(hiddenOffsetInput.value || '0');
let currentStartDate = hiddenStartDateInput.value || null;
let currentEndDate = hiddenEndDateInput.value || null;

function formatDateISO(date) {
    if (!date || !(date instanceof Date)) return null;
    try { return date.toISOString().split('T')[0]; } catch (e) { return null; }
}

async function loadChart(imgElement, loadingIndicator, apiUrl, params = {}, altTextBase = "Chart") {
    loadingIndicator.style.display = 'block';
    imgElement.classList.remove('visible');
    imgElement.src = "data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7";
    imgElement.alt = `Loading ${altTextBase}...`;

    const queryParams = new URLSearchParams(params).toString();
    const fullUrl = `${apiUrl}?${queryParams}`;

    try {
        const response = await fetch(fullUrl);
        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || `HTTP error! status: ${response.status}`);
        }
        if (!data || !data.chart_uri) {
             throw new Error("Invalid chart data received from server.");
        }

        imgElement.onload = () => { loadingIndicator.style.display = 'none'; imgElement.classList.add('visible'); imgElement.alt = `${altTextBase}`; imgElement.onload = null; };
        imgElement.onerror = () => { console.error(`Error loading image data URI for ${apiUrl}.`); loadingIndicator.innerText = 'Display Error'; loadingIndicator.style.display = 'block'; imgElement.alt = `Error displaying ${altTextBase}`; imgElement.src = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='100' height='100' viewBox='0 0 100 100'%3E%3Crect width='100' height='100' fill='%23eee'/%3E%3Ctext x='50' y='55' font-family='Arial' font-size='12' fill='%23aaa' text-anchor='middle'%3EError%3C/text%3E%3C/svg%3E"; imgElement.onload = null; imgElement.onerror = null; };
        imgElement.src = data.chart_uri;

    } catch (error) {
        console.error(`Error fetching or processing chart data for ${apiUrl}:`, error);
        loadingIndicator.innerText = `Load Error`; loadingIndicator.style.display = 'block';
        imgElement.alt = `Error loading ${altTextBase}: ${error.message}`;
        imgElement.src = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='100' height='100' viewBox='0 0 100 100'%3E%3Crect width='100' height='100' fill='%23eee'/%3E%3Ctext x='50' y='55' font-family='Arial' font-size='12' fill='%23aaa' text-anchor='middle'%3EError%3C/text%3E%3C/svg%3E";
        imgElement.onload = null; imgElement.onerror = null;
    }
}

async function loadPredictionChartAndText(params = {}) {
    predictionChartLoadingIndicator.style.display = 'block';
    predictionChartImage.classList.remove('visible');
    predictionChartImage.src = "data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7";
    predictionChartImage.alt = "Loading Prediction Chart...";
    predictionAnalysisLoadingIndicator.style.display = 'block';
    predictionAnalysisTextDiv.innerHTML = '';

    const chartParams = new URLSearchParams(params).toString();
    const chartApiUrl = `/api/prediction-chart?${chartParams}`;
    const analysisApiUrl = `/api/spending-prediction?${chartParams}`;

    try {
        const [chartResponse, analysisResponse] = await Promise.all([
            fetch(chartApiUrl),
            fetch(analysisApiUrl)
        ]);

        const chartData = await chartResponse.json();
        if (!chartResponse.ok) { throw new Error(chartData.error || `Chart HTTP error! status: ${chartResponse.status}`); }
        if (!chartData || !chartData.chart_uri) { throw new Error("Invalid prediction chart data received."); }

        predictionChartImage.onload = () => { predictionChartLoadingIndicator.style.display = 'none'; predictionChartImage.classList.add('visible'); predictionChartImage.alt = "Spending Prediction Chart"; predictionChartImage.onload = null; };
        predictionChartImage.onerror = () => { console.error("Error loading prediction chart image URI."); predictionChartLoadingIndicator.innerText = 'Display Error'; predictionChartLoadingIndicator.style.display = 'block'; predictionChartImage.alt = 'Error displaying prediction chart'; predictionChartImage.src = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='100' height='100' viewBox='0 0 100 100'%3E%3Crect width='100' height='100' fill='%23eee'/%3E%3Ctext x='50' y='55' font-family='Arial' font-size='12' fill='%23aaa' text-anchor='middle'%3EError%3C/text%3E%3C/svg%3E"; predictionChartImage.onload = null; predictionChartImage.onerror = null; };
        predictionChartImage.src = chartData.chart_uri;

        const analysisData = await analysisResponse.json();
        if (!analysisResponse.ok) { throw new Error(analysisData.error || `Analysis HTTP error! status: ${analysisResponse.status}`); }
        if (!analysisData || typeof analysisData.analysis_text === 'undefined') { throw new Error("Invalid prediction analysis data received."); }
        predictionAnalysisTextDiv.innerHTML = analysisData.analysis_text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>').replace(/\*(.*?)\*/g, '<em>$1</em>').replace(/\n/g, '<br>');

    } catch (error) {
        console.error('Error fetching prediction data:', error);
         predictionChartLoadingIndicator.innerText = `Chart Load Error`; predictionChartLoadingIndicator.style.display = 'block';
         predictionChartImage.alt = `Error loading prediction chart: ${error.message}`; predictionChartImage.src = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='100' height='100' viewBox='0 0 100 100'%3E%3Crect width='100' height='100' fill='%23eee'/%3E%3Ctext x='50' y='55' font-family='Arial' font-size='12' fill='%23aaa' text-anchor='middle'%3EError%3C/text%3E%3C/svg%3E";
         predictionAnalysisTextDiv.innerHTML = `<em>Error loading analysis: ${error.message}</em>`;
    } finally {
        predictionAnalysisLoadingIndicator.style.display = 'none';
    }
}

function updateDashboardState() {
    const now = new Date();
    let timeframeText = "";
    let startDate = null;
    let endDate = null;

    if (currentView === 'month') {
        const targetMonthDate = new Date(now.getFullYear(), now.getMonth() + currentOffset, 1);
        startDate = new Date(targetMonthDate.getFullYear(), targetMonthDate.getMonth(), 1);
        endDate = new Date(targetMonthDate.getFullYear(), targetMonthDate.getMonth() + 1, 0);
        timeframeText = targetMonthDate.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });
    } else if (currentView === 'week') {
        const targetDate = new Date(now); targetDate.setDate(targetDate.getDate() + (currentOffset * 7));
        const dayOfWeek = targetDate.getDay();
        const diffToMonday = dayOfWeek === 0 ? -6 : 1 - dayOfWeek;
        startDate = new Date(targetDate); startDate.setDate(startDate.getDate() + diffToMonday);
        endDate = new Date(startDate); endDate.setDate(startDate.getDate() + 6);
        const options = { month: 'short', day: 'numeric' };
        timeframeText = `${startDate.toLocaleDateString('en-US', options)} - ${endDate.toLocaleDateString('en-US', { ...options, year: 'numeric' })}`;
    } else if (currentView === 'year') {
        const targetYear = now.getFullYear() + currentOffset;
        startDate = new Date(targetYear, 0, 1);
        endDate = new Date(targetYear, 11, 31);
        timeframeText = `${targetYear}`;
    }

    currentStartDate = formatDateISO(startDate);
    currentEndDate = formatDateISO(endDate);
    currentTimeframeSpan.innerText = timeframeText;
    chatPeriodDisplay.textContent = timeframeText;

    hiddenViewInput.value = currentView;
    hiddenOffsetInput.value = currentOffset;
    hiddenStartDateInput.value = currentStartDate;
    hiddenEndDateInput.value = currentEndDate;

    if (!currentStartDate || !currentEndDate) {
         console.error("Date calculation failed, cannot load data.");
         return;
    }

    const commonParams = { view: currentView, start_date: currentStartDate, end_date: currentEndDate };

    loadChart(pieChartImage, pieLoadingIndicator, '/api/pie-chart', commonParams, "Budget vs Spending Chart");
    loadChart(lineChartCategoryImage, lineChartCategoryLoadingIndicator, '/api/line-chart', commonParams, "Category Spending Line Chart");
    loadChart(categoryPieChartImage, categoryPieLoadingIndicator, '/api/category-pie-chart', commonParams, "Category Spending Pie Chart");
    loadPredictionChartAndText({ view: currentView, start_date: currentStartDate });

}

function submitTimeframeForm() {
     hiddenViewInput.value = currentView;
     hiddenOffsetInput.value = currentOffset;
     hiddenStartDateInput.value = '';
     hiddenEndDateInput.value = '';
     timeframeForm.submit();
}

 function addChatMessage(message, isUser) {
     const listItem = document.createElement('li');
     listItem.classList.add(isUser ? 'user-message' : 'bot-message');
     const sanitizedMessage = message.replace(/</g, "<").replace(/>/g, ">");
     listItem.innerHTML = sanitizedMessage.replace(/\n/g, '<br>');
     chatHistory.appendChild(listItem);
     const chatBody = chatPopup.querySelector('.chat-body');
     chatBody.scrollTop = chatBody.scrollHeight;
 }

 async function sendChatMessage(messageToSend = null) {
     const userMessage = messageToSend ?? chatInput.value.trim();
     if (!userMessage) return;

     addChatMessage(userMessage, true);
     chatInput.value = '';
     chatLoadingIndicator.style.display = 'block';
     sendChatButton.disabled = true;
     chatInput.disabled = true;

     try {
          const response = await fetch('/api/chatbot', {
             method: 'POST',
             headers: { 'Content-Type': 'application/json', },
             body: JSON.stringify({
                 prompt: userMessage,
                 start_date: currentStartDate,
                 end_date: currentEndDate,
                 view_type: currentView
             }),
         });
         const data = await response.json();

         if (!response.ok) {
             throw new Error(data.error || `HTTP error ${response.status}`);
         }
         addChatMessage(data.response || "Sorry, I couldn't get a response.", false);

     } catch (error) {
          console.error("Chatbot API error:", error);
          addChatMessage(`Error: ${error.message}`, false);
     } finally {
         chatLoadingIndicator.style.display = 'none';
         sendChatButton.disabled = false;
         chatInput.disabled = false;
         chatInput.focus();
     }
 }

viewSelect.addEventListener('change', () => { currentView = viewSelect.value; currentOffset = 0; submitTimeframeForm(); });
prevButton.addEventListener('click', (event) => { event.preventDefault(); currentOffset--; submitTimeframeForm(); });
nextButton.addEventListener('click', (event) => { event.preventDefault(); currentOffset++; submitTimeframeForm(); });

chatFab.addEventListener('click', () => { chatPopup.classList.toggle('show'); if (chatPopup.classList.contains('show')) { chatInput.focus(); } });
closeChatPopup.addEventListener('click', () => { chatPopup.classList.remove('show'); });
sendChatButton.addEventListener('click', () => sendChatMessage());
chatInput.addEventListener('keypress', (e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendChatMessage(); } });
chatSuggestionsContainer.addEventListener('click', (event) => {
    if (event.target.classList.contains('suggestion-btn')) {
        sendChatMessage(event.target.textContent);
    }
});

document.addEventListener('DOMContentLoaded', () => {
     viewSelect.value = currentView;
     updateDashboardState();
});

