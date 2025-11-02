# Arquitetura Modular do Sistema de Postagem TikTok

## 📋 Visão Geral

Este diretório contém a implementação modular do sistema de postagem de vídeos no TikTok. A refatoração divide o código monolítico original (1032 linhas) em **6 módulos independentes e testáveis**, facilitando manutenção, evolução e debug.

## 🎯 Objetivo da Refatoração

- ✅ **Separação de Responsabilidades**: Cada módulo tem uma função clara e específica
- ✅ **Facilita Manutenção**: Modificações em uma etapa não afetam outras
- ✅ **Testabilidade**: Cada módulo pode ser testado independentemente
- ✅ **Compatibilidade Total**: Interface pública permanece 100% compatível
- ✅ **Escalabilidade**: Fácil adicionar novos recursos ou substituir módulos

## 📦 Estrutura dos Módulos

```
beckend/src/modules/
├── __init__.py                  # Exports públicos
├── README.md                    # Esta documentação
├── video_upload.py              # Módulo 1: Upload e Validação
├── description_handler.py       # Módulo 2: Tratamento da Descrição
├── audience_selector.py         # Módulo 3: Seleção de Audiência
├── post_action.py               # Módulo 4: Ação de Postagem
├── post_confirmation.py         # Módulo 5: Confirmação de Postagem
└── file_manager.py              # Módulo 6: Gerenciamento de Arquivos
```

---

## 🔧 Módulo 1: Upload e Validação (`video_upload.py`)

### Responsabilidades
- Validar arquivo de vídeo (existência, tamanho, formato)
- Navegar para página de upload do TikTok
- Localizar campo de upload (main page ou iframes)
- Enviar arquivo de vídeo
- Monitorar progresso do upload
- Aguardar processamento completo

### Principais Métodos
```python
class VideoUploadModule:
    def validate_video_file(video_path: str) -> bool
    def navigate_to_upload_page() -> bool
    def send_video_file(video_path: str, retry: bool = True) -> bool
    def wait_upload_completion(timeout: int = 300) -> bool
    def upload_video(video_path: str) -> bool  # Método principal
```

### Exemplo de Uso
```python
from modules.video_upload import VideoUploadModule

upload = VideoUploadModule(driver, logger=print)
if upload.upload_video("/path/to/video.mp4"):
    print("Upload concluído!")
```

---

## 📝 Módulo 2: Tratamento da Descrição (`description_handler.py`)

### Responsabilidades
- Sanitizar texto da descrição (remover emojis inválidos, caracteres de controle)
- Validar e ajustar comprimento (máx 2200 caracteres)
- Localizar campo de descrição na página
- Preencher descrição (JavaScript ou send_keys)
- Verificar se foi preenchida corretamente

### Principais Métodos
```python
class DescriptionModule:
    def sanitize_description(text: str) -> str
    def validate_description_length(text: str, max_length: int = 2200) -> tuple
    def prepare_description(text: str) -> str
    def fill_description(text: str, required: bool = False) -> bool
    def verify_description_filled(expected_text: str) -> bool
    def clear_description() -> bool
    def handle_description(text: str, required: bool, verify: bool) -> bool  # Método principal
```

### Exemplo de Uso
```python
from modules.description_handler import DescriptionModule

desc = DescriptionModule(driver, logger=print)
if desc.handle_description("Meu vídeo #viral", required=False, verify=True):
    print("Descrição preenchida e verificada!")
```

---

## 👥 Módulo 3: Seleção de Audiência (`audience_selector.py`)

### Responsabilidades
- Detectar audiência atual configurada
- Definir tipo de audiência (público, amigos, privado)
- Localizar e interagir com dropdown de audiência
- Suportar múltiplos idiomas
- Verificar configuração

### Principais Métodos
```python
from enum import Enum

class AudienceType(Enum):
    PUBLIC = "public"
    FRIENDS = "friends"
    PRIVATE = "private"

class AudienceModule:
    def detect_current_audience() -> Optional[AudienceType]
    def set_audience(audience_type: AudienceType, required: bool = False) -> bool
    def set_public(required: bool = False) -> bool  # Atalho
    def set_friends_only(required: bool = False) -> bool  # Atalho
    def set_private(required: bool = False) -> bool  # Atalho
    def verify_audience(expected: AudienceType) -> bool
    def handle_audience(audience_type, required, verify) -> bool  # Método principal
```

### Exemplo de Uso
```python
from modules.audience_selector import AudienceModule, AudienceType

audience = AudienceModule(driver, logger=print)
if audience.handle_audience(AudienceType.PUBLIC, required=False, verify=True):
    print("Audiência configurada como pública!")
```

---

## 🚀 Módulo 4: Ação de Postagem (`post_action.py`)

### Responsabilidades
- Localizar e clicar no botão de publicar (15+ seletores robustos)
- Fechar modais de bloqueio (TUXModal, exit modal)
- Lidar com modal de confirmação
- Detectar violações de conteúdo do TikTok
- Retry automático se necessário
- Salvar screenshots de debug

### Principais Métodos
```python
class PostActionModule:
    def click_publish_button() -> bool
    def close_exit_modal() -> bool
    def close_blocking_modals() -> bool
    def handle_confirmation_dialog() -> bool
    def detect_content_violation() -> bool
    def execute_post(handle_modals: bool, retry_on_exit: bool) -> bool  # Método principal
    def is_on_upload_page() -> bool
    def publish_button_exists() -> bool
```

### Exemplo de Uso
```python
from modules.post_action import PostActionModule

post = PostActionModule(driver, logger=print)
if post.execute_post(handle_modals=True, retry_on_exit=True):
    print("Postagem iniciada!")
```

---

## ✅ Módulo 5: Confirmação de Postagem (`post_confirmation.py`)

### Responsabilidades
- Verificar mudança de URL (sinais de sucesso)
- Verificar desaparecimento do botão de publicar
- Detectar mensagens de sucesso na página
- Monitorar progresso de publicação
- Aguardar confirmação final (com timeout)
- Fornecer status detalhado

### Principais Métodos
```python
class PostConfirmationModule:
    def check_url_changed() -> bool
    def check_publish_button_disappeared() -> bool
    def check_success_message() -> Optional[str]
    def wait_for_confirmation(timeout: int = 60) -> bool
    def verify_post_success() -> bool  # Verificação rápida
    def confirm_posted(timeout: int, quick_check: bool) -> bool  # Método principal
    def get_post_status() -> dict
    def print_status()
```

### Exemplo de Uso
```python
from modules.post_confirmation import PostConfirmationModule

confirm = PostConfirmationModule(driver, logger=print)
if confirm.confirm_posted(timeout=60, quick_check=False):
    print("Vídeo postado com sucesso!")
    confirm.print_status()  # Debug
```

---

## 📁 Módulo 6: Gerenciamento de Arquivos (`file_manager.py`)

### Responsabilidades
- Ler/escrever/deletar arquivos JSON
- Mover/copiar/deletar vídeos
- Criar/remover/verificar locks de postagem
- Obter metadados de vídeos
- Limpar arquivos de postagens falhadas
- Finalizar postagens bem-sucedidas (mover para pasta `posted`)
- Listar vídeos em diretórios

### Principais Métodos
```python
class FileManagerModule:
    # JSON
    def read_json(file_path: str) -> Optional[Dict]
    def write_json(file_path: str, data: Dict) -> bool
    def delete_json(file_path: str, safe: bool = True) -> bool

    # Vídeos
    def move_video(source: str, destination_dir: str, overwrite: bool) -> Optional[str]
    def copy_video(source: str, destination_dir: str, overwrite: bool) -> Optional[str]
    def delete_video(file_path: str, safe: bool = True) -> bool

    # Locks
    def create_lock(file_path: str) -> bool
    def remove_lock(file_path: str) -> bool
    def check_lock(file_path: str, max_age_seconds: Optional[int]) -> bool

    # Organização
    def cleanup_failed_post(video_path: str) -> bool
    def finalize_successful_post(video_path: str, posted_dir: str, keep_original: bool) -> bool

    # Utilitários
    def get_video_metadata(video_path: str) -> Optional[Dict]
    def list_videos_in_directory(directory: str, extensions: tuple) -> list
    def get_file_size_mb(file_path: str) -> Optional[float]
```

### Exemplo de Uso
```python
from modules.file_manager import FileManagerModule

fm = FileManagerModule(logger=print)

# Criar lock
fm.create_lock("/videos/video1.mp4")

# Finalizar postagem
fm.finalize_successful_post(
    video_path="/videos/video1.mp4",
    posted_dir="/posted",
    keep_original=False
)
```

---

## 🎬 Usando o Uploader Modular

### Migração do Código Antigo

O novo uploader é **100% compatível** com o antigo. Basta trocar o import:

```python
# ANTES (uploader.py)
from uploader import TikTokUploader

# DEPOIS (uploader_modular.py)
from uploader_modular import TikTokUploader
```

### Exemplo Completo
```python
from uploader_modular import TikTokUploader
from driver_simple import build_driver

# Cria driver
driver = build_driver(headless=True)

# Cria uploader
uploader = TikTokUploader(
    driver=driver,
    logger=print,
    account_name="minha_conta"
)

# Posta vídeo (método simples)
success = uploader.post_video(
    video_path="/videos/meu_video.mp4",
    description="Descrição do meu vídeo #viral"
)

if success:
    print("✅ Vídeo postado com sucesso!")
else:
    print("❌ Falha ao postar vídeo")

driver.quit()
```

### Uso Avançado (Controle Granular)
```python
# Acessa módulos individuais para controle fino
uploader = TikTokUploader(driver, logger=print)

# Etapa 1: Upload
if not uploader.go_to_upload():
    print("Falha ao acessar página")
    exit(1)

if not uploader.send_file("/videos/video.mp4"):
    print("Falha no upload")
    exit(1)

# Etapa 2: Descrição
uploader.fill_description("Minha descrição")

# Etapa 3: Audiência
uploader.audience_module.set_friends_only(required=False)

# Etapa 4: Publicar
if not uploader.click_publish():
    print("Falha ao publicar")
    exit(1)

uploader.handle_confirmation_dialog()

# Etapa 5: Confirmar
if uploader.confirm_posted():
    print("✅ Sucesso!")

    # Etapa 6: Organizar arquivos
    uploader.finalize_successful_post(
        video_path="/videos/video.mp4",
        posted_dir="/posted"
    )
```

---

## 🧪 Testando Módulos Individualmente

Cada módulo pode ser testado de forma isolada:

```python
# Teste isolado do módulo de descrição
from modules.description_handler import DescriptionModule

desc_module = DescriptionModule(driver, logger=print)

# Testa sanitização
text = "Texto com emoji 🚀 e caracteres especiais\x00"
sanitized = desc_module.sanitize_description(text)
print(f"Sanitizado: {sanitized}")

# Testa validação de comprimento
long_text = "a" * 3000
is_valid, adjusted = desc_module.validate_description_length(long_text)
print(f"Válido: {is_valid}, Ajustado para: {len(adjusted)} chars")
```

---

## 📊 Comparação: Antes vs Depois

| Aspecto | uploader.py (Antes) | uploader_modular.py (Depois) |
|---------|---------------------|------------------------------|
| **Linhas de código** | 1032 linhas | ~400 linhas (+ 6 módulos) |
| **Testabilidade** | Difícil (monolítico) | Fácil (módulos isolados) |
| **Manutenção** | Difícil (código acoplado) | Fácil (separação clara) |
| **Debug** | Difícil (tudo junto) | Fácil (módulo específico) |
| **Extensibilidade** | Difícil (modificar tudo) | Fácil (trocar/adicionar módulo) |
| **Compatibilidade** | - | 100% compatível |

---

## 🔄 Migração Gradual

A refatoração permite migração gradual:

1. **Fase 1**: Manter `uploader.py` funcionando (produção)
2. **Fase 2**: Testar `uploader_modular.py` em desenvolvimento
3. **Fase 3**: Trocar import em código crítico
4. **Fase 4**: Deprecar `uploader.py`

```python
# Configuração flexível
USE_MODULAR_UPLOADER = os.getenv("USE_MODULAR_UPLOADER", "false") == "true"

if USE_MODULAR_UPLOADER:
    from uploader_modular import TikTokUploader
else:
    from uploader import TikTokUploader  # Fallback para versão antiga
```

---

## 🎯 Próximos Passos

- [ ] Criar testes unitários para cada módulo
- [ ] Criar testes de integração end-to-end
- [ ] Adicionar type hints completos
- [ ] Documentar edge cases conhecidos
- [ ] Criar exemplos de uso avançado
- [ ] Medir performance (comparar com versão antiga)
- [ ] Adicionar CI/CD para testes automatizados

---

## 📚 Recursos Adicionais

- [Selenium Documentation](https://www.selenium.dev/documentation/)
- [Python Type Hints](https://docs.python.org/3/library/typing.html)
- [Clean Code Principles](https://www.amazon.com/Clean-Code-Handbook-Software-Craftsmanship/dp/0132350882)

---

## 📝 Changelog

### v2.0 (2025-11-02) - Refatoração Modular
- ✨ Criados 6 módulos independentes
- ✨ Interface 100% compatível com código antigo
- ✨ Documentação completa
- ✨ Melhor separação de responsabilidades
- ✨ Facilita testes e manutenção

### v1.0 (anterior) - Versão Monolítica
- ✅ uploader.py funcional (1032 linhas)
- ⚠️ Difícil manter e testar

---

**Desenvolvido para facilitar manutenção e evolução do sistema de postagem TikTok** 🚀
