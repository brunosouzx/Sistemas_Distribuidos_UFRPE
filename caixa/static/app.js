// Configuração da API
const API_URL = "http://localhost:5000";

// Estado da aplicação
let state = {
  cardapio: [],
  pedidos: [],
  carrinho: [],
  filtroStatus: "todos",
};

// Elementos DOM
const elements = {
  inputCliente: document.getElementById("inputCliente"),
  inputObservacao: document.getElementById("inputObservacao"),
  cardapioList: document.getElementById("cardapioList"),
  loadingCardapio: document.getElementById("loadingCardapio"),
  btnFazerPedido: document.getElementById("btnFazerPedido"),
  btnMeusPedidos: document.getElementById("btnMeusPedidos"),
  btnVoltar: document.getElementById("btnVoltar"),
  sectionNovoPedido: document.getElementById("sectionNovoPedido"),
  sectionPedidos: document.getElementById("sectionPedidos"),
  pedidosList: document.getElementById("pedidosList"),
  loadingPedidos: document.getElementById("loadingPedidos"),
  pedidoResumo: document.getElementById("pedidoResumo"),
  resumoCliente: document.getElementById("resumoCliente"),
  resumoItem: document.getElementById("resumoItem"),
  resumoValor: document.getElementById("resumoValor"),
  resumoObs: document.getElementById("resumoObs"),
  modalSucesso: document.getElementById("modalSucesso"),
  modalErro: document.getElementById("modalErro"),
  modalMensagem: document.getElementById("modalMensagem"),
  modalErroMensagem: document.getElementById("modalErroMensagem"),
  btnOkModal: document.getElementById("btnOkModal"),
  btnOkErro: document.getElementById("btnOkErro"),
};

// Inicialização
document.addEventListener("DOMContentLoaded", () => {
  carregarCardapio();
  setupEventListeners();
});

// Event Listeners
function setupEventListeners() {
  // Navegação
  elements.btnMeusPedidos.addEventListener("click", mostrarPedidos);
  elements.btnVoltar.addEventListener("click", mostrarNovoPedido);

  // Formulário
  elements.inputCliente.addEventListener("input", atualizarResumo);
  elements.inputObservacao.addEventListener("input", atualizarResumo);
  elements.btnFazerPedido.addEventListener("click", fazerPedido);

  // Modais
  elements.btnOkModal.addEventListener("click", () => {
    fecharModal(elements.modalSucesso);
    limparFormulario();
  });
  elements.btnOkErro.addEventListener("click", () => {
    fecharModal(elements.modalErro);
  });

  document.querySelectorAll(".close").forEach((closeBtn) => {
    closeBtn.addEventListener("click", function () {
      fecharModal(this.closest(".modal"));
    });
  });

  // Filtros de pedidos
  document.querySelectorAll(".filter-btn").forEach((btn) => {
    btn.addEventListener("click", function () {
      document
        .querySelectorAll(".filter-btn")
        .forEach((b) => b.classList.remove("active"));
      this.classList.add("active");
      state.filtroStatus = this.dataset.status;
      renderizarPedidos();
    });
  });
}

// API Calls
async function carregarCardapio() {
  try {
    elements.loadingCardapio.style.display = "block";
    const response = await fetch(`${API_URL}/cardapio`);
    const data = await response.json();
    state.cardapio = data.cardapio;
    renderizarCardapio();
  } catch (error) {
    console.error("Erro ao carregar cardápio:", error);
    mostrarErro("Erro ao carregar o cardápio.");
  } finally {
    elements.loadingCardapio.style.display = "none";
  }
}

async function fazerPedido() {
  const cliente = elements.inputCliente.value.trim();
  const observacao = elements.inputObservacao.value.trim();

  if (!cliente || state.carrinho.length === 0) {
    mostrarErro("Adicione pelo menos um item ao carrinho!");
    return;
  }

  try {
    elements.btnFazerPedido.disabled = true;
    elements.btnFazerPedido.textContent = "Processando...";

    const pedidosCriados = [];
    let erros = [];

    for (const itemCarrinho of state.carrinho) {
      for (let i = 0; i < itemCarrinho.quantidade; i++) {
        try {
          const pedidoData = {
            cliente: cliente,
            item: itemCarrinho.item.nome,
          };
          if (observacao) pedidoData.observacao = observacao;

          const response = await fetch(`${API_URL}/pedidos`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(pedidoData),
          });

          const data = await response.json();
          if (response.ok) {
            pedidosCriados.push(data.pedido);
          } else {
            erros.push(`${itemCarrinho.item.nome}: ${data.erro}`);
          }
        } catch (err) {
          erros.push(`${itemCarrinho.item.nome}: ${err.message}`);
        }
      }
    }

    if (pedidosCriados.length > 0) {
      const valorTotal = pedidosCriados.reduce((sum, p) => sum + p.valor, 0);
      const idsPedidos = pedidosCriados.map((p) => `#${p.id}`).join(", ");
      let mensagem = `Pedidos ${idsPedidos} realizados! Total: R$ ${valorTotal.toFixed(2)}`;
      if (erros.length > 0) mensagem += `\n\nFalhas: ${erros.length}`;
      mostrarSucesso(mensagem);
    } else {
      throw new Error(erros.join("\n") || "Erro ao criar pedidos");
    }
  } catch (error) {
    mostrarErro(error.message);
  } finally {
    elements.btnFazerPedido.disabled = false;
    elements.btnFazerPedido.textContent = "Fazer Pedido";
  }
}

async function carregarPedidos() {
  try {
    elements.loadingPedidos.style.display = "block";
    const response = await fetch(`${API_URL}/pedidos?limit=50`);
    const data = await response.json();
    state.pedidos = data.pedidos;
    renderizarPedidos();
  } catch (error) {
    console.error("Erro pedidos:", error);
    mostrarErro("Erro ao carregar histórico.");
  } finally {
    elements.loadingPedidos.style.display = "none";
  }
}

// Renderização
function renderizarCardapio() {
  elements.cardapioList.innerHTML = "";
  const lanches = state.cardapio.filter((item) => item.nome.startsWith("X-"));
  const bebidas = state.cardapio.filter((item) => !item.nome.startsWith("X-"));

  if (lanches.length > 0) {
    const title = document.createElement("h4");
    title.textContent = "🍔 Lanches";
    title.style.gridColumn = "1 / -1";
    title.style.marginTop = "10px";
    elements.cardapioList.appendChild(title);
    lanches.forEach((item) => elements.cardapioList.appendChild(criarCardItem(item)));
  }

  if (bebidas.length > 0) {
    const title = document.createElement("h4");
    title.textContent = "🥤 Bebidas";
    title.style.gridColumn = "1 / -1";
    title.style.marginTop = "20px";
    elements.cardapioList.appendChild(title);
    bebidas.forEach((item) => elements.cardapioList.appendChild(criarCardItem(item)));
  }
}

function criarCardItem(item) {
  const card = document.createElement("div");
  card.className = "cardapio-item";
  card.innerHTML = `
        <h4>${item.nome}</h4>
        <p>${item.descricao}</p>
        <div class="preco">R$ ${item.preco.toFixed(2)}</div>
        <button class="btn-add-carrinho">+ Adicionar</button>
    `;
  card.querySelector(".btn-add-carrinho").addEventListener("click", (e) => {
    e.stopPropagation();
    adicionarAoCarrinho(item);
  });
  return card;
}

function adicionarAoCarrinho(item) {
  const existing = state.carrinho.find((i) => i.item.nome === item.nome);
  if (existing) existing.quantidade++;
  else state.carrinho.push({ item: item, quantidade: 1 });
  
  atualizarResumo();
  
  const toast = document.createElement("div");
  toast.className = "toast-notification";
  toast.textContent = `${item.nome} adicionado!`;
  document.body.appendChild(toast);
  setTimeout(() => toast.remove(), 2000);
}

function removerDoCarrinho(nomeItem) {
  const index = state.carrinho.findIndex((i) => i.item.nome === nomeItem);
  if (index !== -1) {
    if (state.carrinho[index].quantidade > 1) state.carrinho[index].quantidade--;
    else state.carrinho.splice(index, 1);
    atualizarResumo();
  }
}

function renderizarPedidos() {
  let pedidosFiltrados = state.pedidos;

  if (state.filtroStatus !== "todos") {
    pedidosFiltrados = state.pedidos.filter(
      (p) => p.status === state.filtroStatus
    );
  }

  if (pedidosFiltrados.length === 0) {
    elements.pedidosList.innerHTML = '<p class="loading">Nenhum pedido encontrado.</p>';
    return;
  }

  elements.pedidosList.innerHTML = "";
  pedidosFiltrados.reverse().forEach((pedido) => {
    elements.pedidosList.appendChild(criarPedidoCard(pedido));
  });
}

function criarPedidoCard(pedido) {
  const card = document.createElement("div");
  
  // Verifica se é cancelado para mudar o estilo
  if (pedido.status === 'CANCELADO') {
      card.className = "pedido-card cancelado"; // Adiciona classe CSS extra
  } else {
      card.className = "pedido-card";
  }

  const dataFormatada = new Date(pedido.data_pedido).toLocaleString("pt-BR");

  card.innerHTML = `
        <div class="pedido-header">
            <div class="pedido-id">Pedido #${pedido.id}</div>
            <span class="pedido-status status-${pedido.status}">${pedido.status}</span>
        </div>
        <div class="pedido-info">
            <p><strong>Cliente:</strong> ${pedido.cliente}</p>
            <p><strong>Item:</strong> ${pedido.item}</p>
            ${pedido.observacao ? `<p><strong>Obs:</strong> ${pedido.observacao}</p>` : ""}
            <p><strong>Valor:</strong> R$ ${pedido.valor.toFixed(2)}</p>
            <p><strong>Data:</strong> ${dataFormatada}</p>
        </div>
    `;

  return card;
}

// Navegação e Utilitários
function mostrarNovoPedido() {
  elements.sectionNovoPedido.style.display = "block";
  elements.sectionPedidos.style.display = "none";
}

function mostrarPedidos() {
  elements.sectionNovoPedido.style.display = "none";
  elements.sectionPedidos.style.display = "block";
  carregarPedidos(); // Recarrega sempre que abre a tela
}

function atualizarResumo() {
  const cliente = elements.inputCliente.value.trim();
  const observacao = elements.inputObservacao.value.trim();

  if (state.carrinho.length > 0) {
    elements.pedidoResumo.style.display = "block";
    elements.resumoCliente.textContent = cliente || "—";

    const itensHtml = state.carrinho.map((ic) => `
        <div class="carrinho-item">
          <span class="carrinho-item-nome">${ic.quantidade}x ${ic.item.nome}</span>
          <span class="carrinho-item-preco">R$ ${(ic.item.preco * ic.quantidade).toFixed(2)}</span>
          <button class="btn-remover" onclick="removerDoCarrinho('${ic.item.nome}')">🗑️</button>
        </div>
      `).join("");

    const total = state.carrinho.reduce((sum, ic) => sum + ic.item.preco * ic.quantidade, 0);

    elements.resumoItem.innerHTML = itensHtml;
    elements.resumoValor.textContent = `R$ ${total.toFixed(2)}`;
    elements.resumoObs.textContent = observacao || "Nenhuma";
    elements.btnFazerPedido.disabled = !cliente;
  } else {
    elements.pedidoResumo.style.display = "none";
    elements.btnFazerPedido.disabled = true;
  }
}

window.removerDoCarrinho = removerDoCarrinho;

function limparFormulario() {
  elements.inputCliente.value = "";
  elements.inputObservacao.value = "";
  state.carrinho = [];
  elements.pedidoResumo.style.display = "none";
  elements.btnFazerPedido.disabled = true;
}

function mostrarSucesso(mensagem) {
  elements.modalMensagem.textContent = mensagem;
  elements.modalSucesso.style.display = "block";
}

function mostrarErro(mensagem) {
  elements.modalErroMensagem.textContent = mensagem;
  elements.modalErro.style.display = "block";
}

function fecharModal(modal) {
  modal.style.display = "none";
}

window.onclick = function (event) {
  if (event.target.classList.contains("modal")) fecharModal(event.target);
};