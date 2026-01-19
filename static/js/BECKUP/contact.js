/* Salve como: static/css/contact.css */

/* Botão Flutuante (FAB) - (CORRIGIDO) Bolinha Cinza, 20% Menor */
.contact-fab { 
  position: fixed; 
  right: 20px; 
  bottom: 20px; 
  background: #444444; /* (CORRIGIDO) Bolinha Cinza-Escuro */
  color: #222222;     /* (CORRIGIDO) Envelope Cinza-Mais-Escuro */
  border: none; 
  border-radius: 50%; 
  width: 45px;  /* (CORRIGIDO) 20% Menor (era 56px) */
  height: 45px; /* (CORRIGIDO) 20% Menor (era 56px) */
  box-shadow: 0 4px 12px rgba(0,0,0,.3); 
  cursor: pointer; 
  z-index: 2000; 
  display: flex; 
  align-items: center; 
  justify-content: center; 
  transition: background-color 0.2s ease;
}
.contact-fab:hover {
  background: #555555; /* Cinza um pouco mais claro no hover */
}

/* (NOVO) Estilo para o ícone SVG dentro do botão */
.contact-fab svg {
  width: 22px; /* Ajustado para o novo tamanho */
  height: 22px;
}

/* Fundo do Modal */
.modal-backdrop { 
  display: none; 
  position: fixed; 
  inset: 0; 
  background: rgba(0,0,0,0.6); 
  z-index: 2001; 
  align-items: center; 
  justify-content: center; 
  padding: 10px;
}
.modal-backdrop[aria-hidden="false"] { display: flex; }

/* Layout do Modal (Corrigido) */
.modal-card { 
  background: #fff; 
  color: #111;
  border-radius: 8px; 
  padding: 0; 
  width: 100%; 
  max-width: 500px; 
  box-shadow: 0 12px 36px rgba(0,0,0,.45); 
  max-height: 95vh;
  overflow: hidden; 
}

/* Topo Azul Marinho */
.modal-header-blue {
  background: #000033; 
  color: #FFFFFF;
  padding: 16px 24px;
}
.modal-header-blue h3 {
  margin: 0;
  padding: 0;
  font-family: Arial, Helvetica, sans-serif;
  font-size: 1.4rem;
  text-align: center;
}

/* Conteúdo Branco (com scroll) */
.modal-content-white {
  padding: 20px 24px;
  max-height: calc(95vh - 70px); 
  overflow-y: auto;
}

.modal-card p {
  font-family: Arial, Helvetica, sans-serif;
  line-height: 1.5;
  color: #000;
}
.contact-modal-intro {
  margin-top: 0;
  margin-bottom: 8px;
  font-size: 0.95rem;
}
.contact-modal-intro strong { 
  font-weight: 700;
}
.contact-modal-intro-small {
  margin-top: 0;
  margin-bottom: 12px;
  font-size: 0.9rem;
}
.contact-modal-attention {
  font-size: 0.85rem;
  color: #444;
  margin-top: 0;
  margin-bottom: 16px;
  border-left: 3px solid #ffc107;
  padding-left: 8px;
}

/* Campos do Formulário */
.modal-card label {
  display: block;
  font-size: 0.9rem;
  font-weight: 600;
  margin-bottom: 4px;
  color: #333;
}
.modal-card input,
.modal-card textarea {
  width: 100%;
  box-sizing: border-box;
  padding: 10px;
  border-radius: 6px;
  border: 1px solid #ccc;
  margin-bottom: 10px;
  font-size: 1rem;
}
.contact-phone-group {
  display: flex;
  gap: 8px;
  margin-bottom: 8px;
}
.contact-ddd-field { flex: 0 0 80px; }
.contact-phone-field { flex: 1; }

.contact-char-count {
  text-align: right;
  font-size: 0.85rem;
  color: #555;
  margin-top: -5px;
  margin-bottom: 12px;
}
#contact-form-result { 
  margin-top: 12px; 
  font-weight: 600; 
  font-size: 0.95rem;
}

/* Botões do Modal */
.contact-modal-actions {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
  margin-top: 16px;
}
.modal-card .btn { 
  background: #0b84ff; 
  color: white; 
  border: none; 
  padding: 10px 16px; 
  border-radius: 6px; 
  cursor: pointer; 
  font-size: 1rem;
  font-weight: 600;
}
.modal-card .btn.btn-secondary {
  background: #6c757d;
}

@media (max-width:520px) {
  .contact-fab { width: 45px; height: 45px; }
  .contact-fab svg { width: 20px; height: 20px; }
  .modal-card .btn { padding: 9px 14px; font-size: 0.95rem; }
}