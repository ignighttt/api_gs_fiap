const grid = document.querySelector('#cars-grid');
const modal = document.querySelector('#car-modal');
const modalBody = document.querySelector('#modal-body');
const filters = document.querySelectorAll('[data-category]');
let currentCategory = 'Todos';
let searchTerm = '';
let onlyFavorites = false;
let cars = [];
const favorites = new Set(JSON.parse(localStorage.getItem('autovendas-favs') || '[]'));
const money = number => Number(number).toLocaleString('pt-BR', {style:'currency',currency:'BRL',maximumFractionDigits:0});
const number = value => Number(value).toLocaleString('pt-BR');
const escapeHTML = value => String(value).replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
const updateFavoriteCount = () => document.querySelector('#favorite-count').textContent = favorites.size;

async function loadCars() {
  grid.innerHTML = '<p class="loading">Carregando veículos...</p>';
  document.querySelector('#status-message').textContent = '';
  const params = new URLSearchParams({limit:100});
  if (searchTerm) params.set('q',searchTerm);
  if (currentCategory !== 'Todos') params.set('category',currentCategory);
  try {
    const response = await fetch('/api/cars?' + params);
    if (!response.ok) throw new Error('Não foi possível carregar os veículos.');
    const result = await response.json();
    cars = result.items;
    renderCars();
  } catch(err) {
    grid.innerHTML = '<div class="empty-state">Não foi possível carregar o catálogo. Atualize a página.</div>';
    document.querySelector('#status-message').textContent = err.message;
  }
}
function renderCars() {
  const visible = onlyFavorites ? cars.filter(car => favorites.has(car.id)) : cars;
  document.querySelector('#results-count').textContent = `${visible.length} veículo(s) encontrado(s)`;
  if (!visible.length) {grid.innerHTML = '<div class="empty-state">Nenhum veículo encontrado. Experimente outra busca ou categoria.</div>';return;}
  grid.innerHTML = visible.map(car => `<article class="car-card">
    <div class="car-image"><img src="${escapeHTML(car.image_url)}" alt="${escapeHTML(car.brand + ' ' + car.model)}" loading="lazy">
      ${car.featured ? '<span class="car-badge">DESTAQUE</span>' : ''}
      <button class="favorite ${favorites.has(car.id)?'active':''}" type="button" data-fav="${car.id}" aria-label="Alternar favorito" aria-pressed="${favorites.has(car.id)}">${favorites.has(car.id)?'♥':'♡'}</button></div>
    <div class="car-content"><h3>${escapeHTML(car.brand)} ${escapeHTML(car.model)}</h3><p class="car-version">${escapeHTML(car.version)}</p>
    <div class="car-meta"><span>◷ ${car.year}</span><span>◈ ${number(car.mileage)} km</span><span>${escapeHTML(car.category)}</span></div>
    <div class="car-bottom"><strong>${money(car.price)}</strong><button type="button" class="detail-btn" data-detail="${car.id}">Ver detalhes →</button></div></div></article>`).join('');
}
function openDetails(id) {
  const car = cars.find(c => c.id === id);
  if (!car) return;
  modalBody.innerHTML = `<img class="modal-car-img" src="${escapeHTML(car.image_url)}" alt="${escapeHTML(car.brand+' '+car.model)}">
  <h2 id="modal-title">${escapeHTML(car.brand)} ${escapeHTML(car.model)}</h2><p>${escapeHTML(car.version)} · ${car.year} · ${number(car.mileage)} km</p>
  <div class="modal-price">${money(car.price)}</div><p>${escapeHTML(car.description)}</p><h3>Tenho interesse neste veículo</h3>
  <form id="lead-form" class="lead-form"><label>Nome completo<input name="name" required minlength="2" maxlength="100"></label>
  <label>E-mail<input name="email" type="email" required maxlength="254"></label><label>Telefone<input name="phone" type="tel" required minlength="8" maxlength="25"></label>
  <label>Mensagem (opcional)<textarea name="message" maxlength="1000" rows="2" placeholder="Gostaria de saber mais sobre o veículo..."></textarea></label>
  <button type="submit">Enviar interesse</button><p id="lead-result" class="lead-result" role="status"></p></form>`;
  modal.showModal();
  document.querySelector('#lead-form').addEventListener('submit', async event => {
    event.preventDefault();
    const form = event.currentTarget;
    const button = form.querySelector('button');
    const message = form.querySelector('#lead-result');
    button.disabled = true;
    const data = Object.fromEntries(new FormData(form).entries());
    data.car_id = car.id;
    try {
      const response = await fetch('/api/leads',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
      const result = await response.json();
      if (!response.ok) throw new Error(result.error || 'Erro ao registrar interesse.');
      message.textContent = result.message;
      form.reset();
    } catch(error) {message.textContent=error.message;message.style.color='#b42318';}
    finally {button.disabled=false;}
  });
}
grid.addEventListener('click', event => {
  const fav = event.target.closest('[data-fav]');
  if (fav) {
    const id = Number(fav.dataset.fav);
    favorites.has(id) ? favorites.delete(id) : favorites.add(id);
    localStorage.setItem('autovendas-favs',JSON.stringify([...favorites]));
    updateFavoriteCount(); renderCars();return;
  }
  const detail = event.target.closest('[data-detail]');
  if (detail) openDetails(Number(detail.dataset.detail));
});
filters.forEach(button => button.addEventListener('click', () => {
  currentCategory = button.dataset.category;
  filters.forEach(el => el.classList.toggle('active',el === button));
  loadCars();
}));
document.querySelector('#search-form').addEventListener('submit', event => {
  event.preventDefault();searchTerm = document.querySelector('#search-input').value.trim();
  document.querySelector('#veiculos').scrollIntoView({behavior:'smooth'});loadCars();
});
document.querySelector('#favorites-toggle').addEventListener('click',event => {
  onlyFavorites = !onlyFavorites;
  event.currentTarget.setAttribute('aria-pressed',String(onlyFavorites));
  event.currentTarget.style.background=onlyFavorites?'#2563eb':'';
  document.querySelector('#veiculos').scrollIntoView({behavior:'smooth'});renderCars();
});
document.querySelector('#close-modal').addEventListener('click',() => modal.close());
modal.addEventListener('click',event => {if (event.target === modal) modal.close();});
document.querySelector('#year').textContent = new Date().getFullYear();
updateFavoriteCount();loadCars();
