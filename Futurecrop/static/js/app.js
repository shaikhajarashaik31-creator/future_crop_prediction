const form = document.querySelector('#prediction-form');
const emptyState = document.querySelector('#empty-state');
const resultContent = document.querySelector('#result-content');
const loadingState = document.querySelector('#loading-state');
const errorMessage = document.querySelector('#error-message');
const submitButton = form.querySelector('button[type="submit"]');
const monthInput = form.elements.month;

const currentMonth = new Date();
monthInput.min = `${currentMonth.getFullYear()}-${String(currentMonth.getMonth() + 1).padStart(2, '0')}`;

function formatPrice(value) {
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0,
  }).format(value);
}

function formatMonth(month) {
  const [year, number] = month.split('-').map(Number);
  return new Intl.DateTimeFormat('en-IN', { month: 'long', year: 'numeric' })
    .format(new Date(year, number - 1, 1));
}

function showState(state) {
  emptyState.hidden = state !== 'empty';
  loadingState.hidden = state !== 'loading';
  resultContent.hidden = state !== 'result';
  errorMessage.hidden = state !== 'error';
}

function renderResult(data) {
  const current = Number(data.currentPrice);
  const predicted = Number(data.predictedPrice);
  const difference = predicted - current;
  const percentChange = current ? (difference / current) * 100 : 0;
  const scale = Math.max(current, predicted, 1);
  const crop = data.crop.charAt(0).toUpperCase() + data.crop.slice(1);

  document.querySelector('#result-title').textContent = `${crop} outlook`;
  document.querySelector('#result-location').textContent = data.state;
  document.querySelector('#result-month').textContent = formatMonth(data.month);
  document.querySelector('#predicted-price').textContent = formatPrice(predicted);
  document.querySelector('#current-price').textContent = formatPrice(current);
  document.querySelector('#comparison-predicted').textContent = formatPrice(predicted);
  document.querySelector('#price-change').textContent = `${difference >= 0 ? '+' : ''}${percentChange.toFixed(1)}% vs current`;
  document.querySelector('#current-bar').style.width = `${Math.max(4, (current / scale) * 100)}%`;
  document.querySelector('#predicted-bar').style.width = `${Math.max(4, (predicted / scale) * 100)}%`;

  const sourceNote = data.method === 'mock-data'
    ? 'Current price uses the latest matching record in the supplied market data.'
    : 'No matching market record was found; current price uses the backend fallback estimate.';
  document.querySelector('#source-note').textContent = sourceNote;
  showState('result');
}

form.addEventListener('submit', async (event) => {
  event.preventDefault();
  if (!form.reportValidity()) return;

  const formData = new FormData(form);
  const request = {
    state: formData.get('state'),
    district: formData.get('district').trim() || null,
    market: formData.get('market') || null,
    crop: formData.get('crop').trim(),
    month: formData.get('month'),
  };

  showState('loading');
  submitButton.disabled = true;

  try {
    const response = await fetch('/predict', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
    });
    const data = await response.json();
    if (!response.ok) {
      const detail = typeof data.detail === 'string' ? data.detail : 'Check the fields and try again.';
      throw new Error(detail);
    }
    renderResult(data);
  } catch (error) {
    errorMessage.textContent = error instanceof TypeError
      ? 'Could not reach the prediction service. Check that the FutureCrop server is running and try again.'
      : error.message;
    showState('error');
  } finally {
    submitButton.disabled = false;
  }
});