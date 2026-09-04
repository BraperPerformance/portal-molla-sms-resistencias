# Central do Cliente · SMS Resistências Elétricas

Portal estático de documentos. Arquivo único: todo o HTML, CSS, JS e os documentos
(embutidos em base64) estão dentro do `index.html`. Sem build, sem dependências.

## Deploy

GitHub → Vercel → Add New Project → Framework Preset **Other** →
Build Command e Output Directory em branco → Deploy.

## Acesso

Protegido por credencial de acesso solicitada na tela de login.

> **Aviso de segurança.** A credencial é validada no navegador e fica visível no
> código-fonte. A barreira serve para organizar e apresentar o material, **não**
> como proteção de conteúdo confidencial. Para material sensível, use autenticação
> de servidor (ex.: Vercel Password Protection).

## Atualizar documentos

Edite o `config.json` e rode novamente o gerador.

---
© 2026 Agência Molla
