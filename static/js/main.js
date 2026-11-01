function setTopupQr(form) {
  const amount = form.querySelector('[name="amount"]').value;
  const image = form.querySelector('.topup-qr');
  if (!image) return;
  const safeAmount = Number.parseInt(amount, 10);
  if (!Number.isFinite(safeAmount) || safeAmount <= 0) return;
  const username = encodeURIComponent(image.dataset.username);
  image.src = `https://img.vietqr.io/image/MB-0966618840-compact2.png?amount=${safeAmount}&addInfo=NAPTHE%20${username}&accountName=HOANG%20MINH%20QUAN`;
}

const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content;
document.querySelectorAll('form[method="post"]').forEach((form) => {
  if (csrfToken && !form.querySelector('[name="_csrf_token"]')) {
    const input = document.createElement('input');
    input.type = 'hidden';
    input.name = '_csrf_token';
    input.value = csrfToken;
    form.append(input);
  }
  if (!form.matches('[data-monthly-form]')) {
    form.addEventListener('submit', (event) => {
      const button = event.submitter;
      if (button) {
        button.disabled = true;
        button.textContent = 'Đang xử lý…';
      }
    });
  }
});

document.addEventListener('input', (event) => {
  if (event.target.matches('form[action="/portal/topup"] [name="amount"]')) {
    setTopupQr(event.target.form);
  }
});

document.addEventListener('click', (event) => {
  const amountButton = event.target.closest('[data-amount]');
  if (amountButton) {
    const input = amountButton.closest('form').querySelector('[name="amount"]');
    input.value = amountButton.dataset.amount;
    input.dispatchEvent(new Event('input', { bubbles: true }));
    input.focus();
  }
  if (event.target.closest('[data-outsider]')) {
    document.getElementById('verify-actions').classList.add('hidden');
    document.getElementById('outsider').classList.remove('hidden');
  }
  if (event.target.closest('[data-close-monthly]')) {
    document.querySelector('[data-monthly-payment]').classList.add('hidden');
  }
  if (event.target.closest('[data-confirm-monthly]')) {
    const form = document.querySelector('[data-monthly-form]');
    if (!form.reportValidity()) return;
    form.querySelector('[name="confirmed_payment"]').value = '1';
    event.target.disabled = true;
    event.target.textContent = 'Đang gửi…';
    form.submit();
  }
});

document.querySelector('[data-monthly-form]')?.addEventListener('submit', (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  const vehicle = form.querySelector('[name="vehicle"]:checked')?.value;
  const plate = form.querySelector('[name="plate"]');
  if (vehicle === 'Xe máy' && !plate.value.trim()) {
    plate.setCustomValidity('Vui lòng nhập biển số xe máy.');
    plate.reportValidity();
    plate.addEventListener('input', () => plate.setCustomValidity(''), { once: true });
    return;
  }
  const amount = vehicle === 'Xe đạp' ? 45000 : 70000;
  const username = document.querySelector('.topup-qr').dataset.username;
  const modal = document.querySelector('[data-monthly-payment]');
  modal.querySelector('[data-pass-amount]').textContent = `${amount.toLocaleString('vi-VN')}đ`;
  modal.querySelector('[data-pass-memo]').textContent = `THANG ${username} ${vehicle} ${plate.value.trim()}`;
  modal.querySelector('[data-pass-qr]').src = `https://img.vietqr.io/image/MB-0966618840-compact2.png?amount=${amount}&addInfo=THANG%20${encodeURIComponent(username)}&accountName=HOANG%20MINH%20QUAN`;
  modal.classList.remove('hidden');
});

document.querySelectorAll('[data-monthly-form] [name="vehicle"]').forEach((radio) => {
  radio.addEventListener('change', () => {
    const form = radio.form;
    const plate = form.querySelector('[name="plate"]');
    const isMotorbike = form.querySelector('[name="vehicle"]:checked')?.value === 'Xe máy';
    plate.required = isMotorbike;
    if (!isMotorbike) plate.value = '';
    form.querySelector('[data-plate-wrap]').classList.toggle('opacity-50', !isMotorbike);
  });
});
document.querySelectorAll('[data-monthly-form]').forEach((form) => {
  const selectedVehicle = form.querySelector('[name="vehicle"]:checked')?.value;
  form.querySelector('[name="plate"]').required = selectedVehicle === 'Xe máy';
});

const assistantPanel = document.querySelector('#assistant-panel');
const assistantToggle = document.querySelector('#assistant-toggle');
const assistantMessages = document.querySelector('#assistant-messages');
const assistantForm = document.querySelector('#assistant-form');
const assistantInput = document.querySelector('#assistant-input');
const pagePath = document.body.dataset.pagePath || '/';
const neuAuthenticated = document.body.dataset.neuAuthenticated === 'true';
const membershipKey = 'neu-onecard-membership';
const historyKey = 'neu-onecard-assistant-history';
let assistantHistory = [];
try { assistantHistory = JSON.parse(sessionStorage.getItem(historyKey) || '[]').slice(-10); } catch { assistantHistory = []; }

function showAssistant(open = true) {
  assistantPanel.hidden = !open;
  assistantToggle.setAttribute('aria-expanded', String(open));
  if (open) assistantInput.focus({ preventScroll: true });
}

function addAssistantMessage(role, message, pending = false) {
  const bubble = document.createElement('div');
  bubble.className = `assistant-message ${role}${pending ? ' pending' : ''}`;
  bubble.textContent = message;
  assistantMessages.append(bubble);
  assistantMessages.scrollTop = assistantMessages.scrollHeight;
  return bubble;
}

function rememberMessage(role, text) {
  assistantHistory.push({ role, text });
  assistantHistory = assistantHistory.slice(-10);
  sessionStorage.setItem(historyKey, JSON.stringify(assistantHistory));
}

async function askGemini(message, visibleUserMessage = true) {
  if (visibleUserMessage) {
    addAssistantMessage('user', message);
    rememberMessage('user', message);
  }
  const pending = addAssistantMessage('assistant', 'Đang xem hướng dẫn của trang...', true);
  const csrf = document.querySelector('meta[name="csrf-token"]')?.content || '';
  try {
    const response = await fetch('/api/assistant', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrf },
      body: JSON.stringify({ message, page: pagePath, history: assistantHistory })
    });
    const data = await response.json();
    pending.remove();
    const reply = data.reply || data.error || 'Trợ lý chưa thể trả lời lúc này.';
    addAssistantMessage('assistant', reply);
    rememberMessage('assistant', reply);
  } catch {
    pending.remove();
    addAssistantMessage('assistant', 'Không kết nối được trợ lý. Bạn có thể dùng các mục trên thanh điều hướng để tiếp tục.');
  }
}

function normalizeVietnamese(text) {
  return text.toLocaleLowerCase('vi').replace(/đ/g, 'd').normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/[.,!?;:'"()-]/g, ' ').replace(/\s+/g, ' ').trim();
}

function answerMembership(message) {
  const normalized = normalizeVietnamese(message);
  const negative = /(^|\s)(khong|khong phai|kh|ko|khum|no|nope|nah|not)(\s|$)/.test(normalized)
    || /not (a )?(neu )?(student|lecturer|staff)/.test(normalized);
  if (negative) {
    sessionStorage.setItem(membershipKey, 'no');
    const reply = 'Xin vui lòng về trường của bạn mà gửi xe.';
    addAssistantMessage('assistant', reply);
    rememberMessage('assistant', reply);
    return true;
  }
  const affirmative = /(^|\s)(co|dung|vang|uh|uhm|yes|yep|yeah|phai)(\s|$)/.test(normalized)
    || /dung vay|chac chan|(^|\s)(thuoc neu|dang hoc tai neu)(\s|$)/.test(normalized)
    || /(toi|minh|em|anh|chi) (la|hien dang la) (sinh vien|giang vien|can bo)|((sinh vien|giang vien|can bo).*neu|neu.*(sinh vien|giang vien|can bo))|i am (a )?(neu )?(student|lecturer|staff)/.test(normalized);
  if (affirmative) {
    sessionStorage.setItem(membershipKey, 'yes');
    const reply = 'Để đăng nhập, hãy dùng mã sinh viên hoặc mã giảng viên làm tên đăng nhập. Mật khẩu khởi tạo là họ tên không dấu, viết liền, chữ thường; nếu đã đổi mật khẩu, hãy dùng mật khẩu hiện tại. Mở trang Đăng nhập trên thanh điều hướng để tiếp tục.';
    addAssistantMessage('assistant', reply);
    rememberMessage('assistant', reply);
    askGemini('Hãy hướng dẫn ngắn gọn cách sử dụng trang hiện tại cho người thuộc NEU.', false);
    return true;
  }
  addAssistantMessage('assistant', 'Bạn vui lòng trả lời Có nếu là sinh viên, giảng viên hoặc cán bộ NEU; nếu không, hãy trả lời Không nhé.');
  return true;
}

assistantToggle?.addEventListener('click', () => showAssistant(assistantPanel.hidden));
document.querySelector('[data-assistant-close]')?.addEventListener('click', () => showAssistant(false));

assistantForm?.addEventListener('submit', async (event) => {
  event.preventDefault();
  const message = assistantInput.value.trim();
  if (!message) return;
  assistantInput.value = '';
  if (!sessionStorage.getItem(membershipKey)) {
    addAssistantMessage('user', message);
    rememberMessage('user', message);
    answerMembership(message);
    return;
  }
  if (sessionStorage.getItem(membershipKey) === 'no') {
    addAssistantMessage('user', message);
    addAssistantMessage('assistant', 'Xin vui lòng về trường của bạn mà gửi xe.');
    return;
  }
  await askGemini(message);
});

if (assistantPanel) {
  if (neuAuthenticated) {
    sessionStorage.setItem(membershipKey, 'yes');
    const hasOldMembershipPrompt = assistantHistory.some((item) =>
      item.role === 'assistant' && normalizeVietnamese(item.text).includes('ban co phai sinh vien neu khong')
    );
    if (hasOldMembershipPrompt) {
      assistantHistory = [];
      sessionStorage.setItem(historyKey, '[]');
      assistantMessages.replaceChildren();
    }
  }
  assistantHistory.forEach((item) => addAssistantMessage(item.role, item.text));
  showAssistant(true);
  const membership = sessionStorage.getItem(membershipKey);
  if (!membership && !neuAuthenticated) {
    assistantMessages.replaceChildren();
    assistantHistory = [];
    sessionStorage.removeItem(historyKey);
    const firstQuestion = 'Bạn có phải sinh viên NEU không?';
    if (assistantHistory.at(-1)?.text !== firstQuestion) {
      addAssistantMessage('assistant', firstQuestion);
      rememberMessage('assistant', firstQuestion);
    }
  } else if (membership === 'no' && !neuAuthenticated) {
    addAssistantMessage('assistant', 'Xin vui lòng về trường của bạn mà gửi xe.');
  } else {
    askGemini('Hãy tự động giới thiệu nội dung và cách sử dụng trang đang mở.', false);
  }
}

function filterUsers() {
  const search = document.querySelector('[data-user-search]');
  const role = document.querySelector('[data-role-filter]');
  if (!search || !role) return;
  const query = search.value.trim().toLocaleLowerCase('vi');
  document.querySelectorAll('[data-user-row]').forEach((row) => {
    const matchesQuery = row.dataset.search.includes(query);
    const matchesRole = !role.value || row.dataset.role === role.value;
    row.hidden = !(matchesQuery && matchesRole);
  });
}

document.querySelector('[data-user-search]')?.addEventListener('input', filterUsers);
document.querySelector('[data-role-filter]')?.addEventListener('change', filterUsers);

document.querySelectorAll('.toast').forEach((item) => {
  setTimeout(() => {
    item.style.opacity = '0';
    item.style.transition = 'opacity .4s';
  }, 6000);
});
