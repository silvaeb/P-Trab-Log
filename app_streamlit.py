import streamlit as st
import pandas as pd
import os
import sys
from datetime import datetime
import tempfile
import re
import json
import base64
import secrets
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.units import mm

# Adicionar o diretório atual ao path para importar módulos locais
sys.path.append('.')

# Tentar importar os módulos locais
try:
    from operacional import GeradorPDFPTrab
    MODULO_OPERACIONAL_CARREGADO = True
except ImportError as e:
    st.error(f"❌ Erro ao carregar módulo operacional: {e}")
    MODULO_OPERACIONAL_CARREGADO = False

try:
    from codom_manager import codom_manager
    CODOM_MANAGER_CARREGADO = True
except ImportError as e:
    st.error(f"❌ Erro ao carregar gerenciador CODOM: {e}")
    CODOM_MANAGER_CARREGADO = False

try:
    from saldo_manager import saldo_manager
    SALDO_MANAGER_CARREGADO = True
except ImportError as e:
    st.error(f"❌ Erro ao carregar gerenciador de saldo: {e}")
    SALDO_MANAGER_CARREGADO = False

try:
    from homologacao_system import homologacao_system
    HOMOLOGACAO_SYSTEM_CARREGADO = True
except ImportError as e:
    st.error(f"❌ Erro ao carregar sistema de homologação: {e}")
    HOMOLOGACAO_SYSTEM_CARREGADO = False

# Sistema de autenticação simplificado
class AuthenticationSystem:
    def __init__(self):
        self.users_file = 'users.json'
        self.tokens_file = 'password_tokens.json'
        self.load_users()
    
    def load_users(self):
        """Carrega os usuários do arquivo JSON"""
        try:
            if os.path.exists(self.users_file):
                with open(self.users_file, 'r', encoding='utf-8') as f:
                    self.users = json.load(f)
            else:
                # Usuário master padrão
                self.users = {
                    "00000000000": {
                        'nome': "ADMINISTRADOR MASTER",
                        'posto': "CEL", 
                        'om': "6122 - 40º BI",
                        'email': "admin@system.com",
                        'password': self.hash_password("Master123!"),
                        'perfil': "master",
                        'data_cadastro': datetime.now().isoformat(),
                        'cadastrado_por': "SISTEMA",
                        'ativo': True
                    }
                }
                self.save_users()
        except Exception as e:
            st.error(f"Erro ao carregar usuários: {e}")
            self.users = {}
    
    def save_users(self):
        """Salva os usuários no arquivo JSON"""
        try:
            with open(self.users_file, 'w', encoding='utf-8') as f:
                json.dump(self.users, f, ensure_ascii=False, indent=2)
        except Exception as e:
            st.error(f"Erro ao salvar usuários: {e}")
    
    def hash_password(self, password):
        """Faz o hash da senha usando SHA-256"""
        import hashlib
        return hashlib.sha256(password.encode()).hexdigest()
    
    def validate_password(self, password):
        """Valida se a senha atende aos requisitos"""
        if len(password) < 6:
            return False, "A senha deve ter pelo menos 6 caracteres"
        
        if not re.search(r'[A-Za-z]', password):
            return False, "A senha deve conter letras"
        
        if not re.search(r'\d', password):
            return False, "A senha deve conter números"
        
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            return False, "A senha deve conter pelo menos um caractere especial"
        
        return True, "Senha válida"
    
    def validate_cpf_simple(self, cpf):
        """Validação SIMPLES do CPF - apenas verifica se tem 11 dígitos"""
        cpf_clean = re.sub(r'\D', '', cpf)
        if len(cpf_clean) != 11:
            return False, "CPF deve conter 11 dígitos"
        return True, cpf_clean
    
    def register_user(self, nome, posto, om, cpf, email, password, perfil="usuário", cadastrado_por="master"):
        """Registra um novo usuário"""
        # Valida CPF SIMPLES
        is_valid_cpf, cpf_result = self.validate_cpf_simple(cpf)
        if not is_valid_cpf:
            return False, cpf_result
        
        cpf_clean = cpf_result
        
        # Verifica se CPF já existe - GARANTIR 1 CADASTRO POR CPF
        if cpf_clean in self.users:
            return False, "CPF já cadastrado"
        
        # Valida senha
        is_valid, msg = self.validate_password(password)
        if not is_valid:
            return False, msg
        
        # Valida email
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            return False, "Email inválido"
        
        # Cria usuário
        self.users[cpf_clean] = {
            'nome': nome.upper(),
            'posto': posto,
            'om': om,
            'email': email.lower(),
            'password': self.hash_password(password),
            'perfil': perfil.lower(),
            'data_cadastro': datetime.now().isoformat(),
            'cadastrado_por': cadastrado_por,
            'ativo': True
        }
        
        self.save_users()
        return True, "Usuário cadastrado com sucesso"
    
    def update_user(self, cpf, updates):
        """Atualiza dados de um usuário"""
        if cpf not in self.users:
            return False, "Usuário não encontrado"
        
        # Atualizar campos permitidos
        allowed_fields = ['nome', 'posto', 'om', 'email', 'perfil', 'ativo', 'password']
        for field, value in updates.items():
            if field in allowed_fields:
                if field == 'nome':
                    self.users[cpf][field] = value.upper()
                elif field == 'email':
                    self.users[cpf][field] = value.lower()
                elif field == 'password':
                    # Se for atualização de senha, fazer o hash
                    self.users[cpf][field] = self.hash_password(value)
                else:
                    self.users[cpf][field] = value
        
        self.save_users()
        return True, "Usuário atualizado com sucesso"
    
    def change_password(self, cpf, current_password, new_password):
        """Altera a senha do usuário após validar a senha atual"""
        if cpf not in self.users:
            return False, "Usuário não encontrado"
        
        # Verificar senha atual
        if self.users[cpf]['password'] != self.hash_password(current_password):
            return False, "Senha atual incorreta"
        
        # Validar nova senha
        is_valid, msg = self.validate_password(new_password)
        if not is_valid:
            return False, msg
        
        # Atualizar senha
        self.users[cpf]['password'] = self.hash_password(new_password)
        self.save_users()
        
        return True, "Senha alterada com sucesso"
    
    def delete_user(self, cpf):
        """Exclui um usuário (apenas master pode excluir)"""
        if cpf not in self.users:
            return False, "Usuário não encontrado"
        
        # Não permitir excluir o próprio usuário master
        if cpf == "00000000000":
            return False, "Não é possível excluir o usuário master"
        
        del self.users[cpf]
        self.save_users()
        return True, "Usuário excluído com sucesso"
    
    def get_users_by_om(self, om_filter):
        """Filtra usuários por Organização Militar"""
        if not om_filter:
            return self.users
        
        filtered_users = {}
        for cpf, user in self.users.items():
            if om_filter.lower() in user['om'].lower():
                filtered_users[cpf] = user
        return filtered_users
    
    def login(self, cpf, password):
        """Realiza o login do usuário - VALIDAÇÃO SIMPLIFICADA"""
        # Limpa o CPF - apenas remove caracteres não numéricos
        cpf_clean = re.sub(r'\D', '', cpf)
        
        print(f"🔍 DEBUG LOGIN - CPF digitado: '{cpf}'")
        print(f"🔍 DEBUG LOGIN - CPF limpo: '{cpf_clean}'")
        print(f"🔍 DEBUG LOGIN - Usuários disponíveis: {list(self.users.keys())}")
        
        # Verifica se tem 11 dígitos
        if len(cpf_clean) != 11:
            return False, "CPF deve conter 11 dígitos"
        
        if cpf_clean not in self.users:
            return False, "CPF não encontrado"
        
        user = self.users[cpf_clean]
        
        if not user['ativo']:
            return False, "Usuário inativo"
        
        # Verifica a senha
        password_hash = self.hash_password(password)
        print(f"🔍 DEBUG LOGIN - Hash da senha digitada: {password_hash}")
        print(f"🔍 DEBUG LOGIN - Hash armazenado: {user['password']}")
        
        if user['password'] != password_hash:
            return False, "Senha incorreta"
        
        return True, user

    def generate_temporary_password(self):
        """Gera uma senha temporária aleatória"""
        import random
        import string
        
        # Gerar senha com 8 caracteres: letras, números e símbolos
        letters = string.ascii_letters
        digits = string.digits
        symbols = "!@#$%&*"
        
        # Garantir pelo menos um de cada tipo
        temp_password = [
            random.choice(letters),
            random.choice(letters.upper()),
            random.choice(digits),
            random.choice(symbols)
        ]
        
        # Completar com caracteres aleatórios
        all_chars = letters + digits + symbols
        temp_password.extend(random.choice(all_chars) for _ in range(4))
        
        # Embaralhar
        random.shuffle(temp_password)
        return ''.join(temp_password)
    
    def send_password_reset_email(self, cpf, temp_password):
        """Envia email com nova senha temporária - CORRIGIDO E FUNCIONAL"""
        cpf_clean = re.sub(r'\D', '', cpf)
        
        if cpf_clean not in self.users:
            return False, "Usuário não encontrado"
        
        user = self.users[cpf_clean]
        email = user['email']
        
        try:
            # IMPLEMENTAÇÃO SIMPLES DE ENVIO DE EMAIL (usando SMTP do Gmail como exemplo)
            import smtplib
            from email.mime.text import MimeText
            from email.mime.multipart import MimeMultipart
            
            # Configurações do servidor SMTP (Gmail)
            smtp_server = "smtp.gmail.com"
            smtp_port = 587
            smtp_username = "seu_email@gmail.com"  # Configure isso no ambiente
            smtp_password = "sua_senha_app"       # Configure isso no ambiente
            
            # Criar mensagem
            subject = "Recuperação de Senha - Sistema de Plano de Trabalho Logístico"
            
            message = f"""
            Prezado(a) {user['nome']},
            
            Você solicitou a recuperação de senha para acesso ao Sistema de Plano de Trabalho Logístico.
            
            Sua nova senha temporária é: {temp_password}
            
            Por segurança, recomendamos que você altere esta senha após o primeiro acesso.
            
            Atenciosamente,
            Sistema de Plano de Trabalho Logístico
            """
            
            # Configurar email
            msg = MimeMultipart()
            msg['From'] = smtp_username
            msg['To'] = email
            msg['Subject'] = subject
            
            msg.attach(MimeText(message, 'plain'))
            
            # Tentar enviar email (apenas se as credenciais estiverem configuradas)
            if smtp_username != "seu_email@gmail.com" and smtp_password != "sua_senha_app":
                server = smtplib.SMTP(smtp_server, smtp_port)
                server.starttls()
                server.login(smtp_username, smtp_password)
                server.send_message(msg)
                server.quit()
                return True, f"Email enviado com sucesso para {email}"
            else:
                # Modo desenvolvimento: mostrar a senha na interface
                return True, f"Modo desenvolvimento - Nova senha: {temp_password}. Configure o SMTP para envio real."
                
        except Exception as e:
            # Em caso de erro, retorna a senha para o usuário
            return True, f"Erro no envio do email: {str(e)}. Sua nova senha é: {temp_password}"

# Instância global do sistema de autenticação
auth_system = AuthenticationSystem()

# Configuração da página
st.set_page_config(
    page_title="Gerador de Plano de Trabalho Logístico",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# CSS personalizado
st.markdown("""
<style>
    /* Remover completamente o header padrão do Streamlit */
    header {
        visibility: hidden;
        height: 0;
    }
    /* Ajustar o container principal para começar no topo */
    .stApp {
        margin-top: -80px;
    }
    /* Header customizado sem margens */
    .header-container {
        margin-top: -20px;
        margin-bottom: 1rem;
    }
    /* Remover padding superior */
    .stApp [data-testid="stAppViewContainer"] {
        padding-top: 0;
    }
    /* Estilos para login */
    .login-container {
        background-color: rgba(255, 255, 255, 0.95);
        padding: 2rem;
        border-radius: 10px;
        margin: 2rem auto;
        max-width: 500px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    .main-header {
        font-size: 2.5rem;
        color: #000000;
        text-align: center;
        margin-bottom: 2rem;
        font-weight: bold;
    }
    .section-header {
        font-size: 1.8rem;
        color: #2e5cb8;
        margin-top: 2rem;
        margin-bottom: 1rem;
        border-bottom: 2px solid #2e5cb8;
        padding-bottom: 0.5rem;
    }
    .success-box {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        border-radius: 5px;
        padding: 15px;
        margin: 10px 0;
    }
    .warning-box {
        background-color: #fff3cd;
        border: 1px solid #ffeaa7;
        border-radius: 5px;
        padding: 15px;
        margin: 10px 0;
    }
    .searchable-select {
        max-height: 200px;
        overflow-y: auto;
        border: 1px solid #ccc;
        border-radius: 4px;
        padding: 8px;
    }
    .racao-box {
        background-color: #e8f4fd;
        border: 1px solid #b8d4f0;
        border-radius: 5px;
        padding: 10px;
        margin: 5px 0;
    }
    /* Ajustes para containers com fundo branco */
    .stTabs [data-baseweb="tab-list"] {
        background-color: rgba(255, 255, 255, 0.95);
        padding: 10px;
        border-radius: 5px;
    }
    .stTab {
        background-color: rgba(255, 255, 255, 0.95);
    }
    /* Container do logo e título */
    .header-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        text-align: center;
        margin-bottom: 1rem;
        padding-top: 0;
    }
    .logo-title {
        width: 80px;
        height: 80px;
    }
    .title-text {
        font-size: 2.5rem;
        color: #000000;
        font-weight: bold;
        margin: 0;
    }
    /* Garantir que o container principal começa no topo */
    .main-container {
        background-color: rgba(255, 255, 255, 0.95);
        padding: 1rem 2rem;
        border-radius: 10px;
        margin: 0;
        margin-top: -20px;
    }
    /* Estilo para campos de formulário */
    .form-field {
        margin-bottom: 1rem;
    }
    /* Estilo para campo de pesquisa OM */
    .om-search-container {
        background-color: #f8f9fa;
        border: 1px solid #dee2e6;
        border-radius: 5px;
        padding: 10px;
        margin-bottom: 10px;
    }
    /* Estilo para card de saldo */
    .saldo-card {
        background-color: #e8f5e8;
        padding: 20px;
        border-radius: 10px;
        border-left: 5px solid #28a745;
        margin-bottom: 20px;
    }
</style>
""", unsafe_allow_html=True)

# Função para carregar imagem de fundo
def add_bg_image():
    try:
        if os.path.exists('intendencia.jpg'):
            with open('intendencia.jpg', "rb") as image_file:
                encoded_string = base64.b64encode(image_file.read()).decode()
            st.markdown(
                f"""
                <style>
                .stApp {{
                    background-image: url("data:image/jpg;base64,{encoded_string}");
                    background-size: cover;
                    background-position: center;
                    background-repeat: no-repeat;
                    background-attachment: fixed;
                }}
                .main-container {{
                    background-color: rgba(255, 255, 255, 0.95);
                    padding: 2rem;
                    border-radius: 10px;
                    margin: 1rem;
                }}
                </style>
                """,
                unsafe_allow_html=True
            )
    except Exception as e:
        print(f"⚠️ Não foi possível carregar imagem de fundo: {e}")

# Lista de postos/gradações
POSTOS_GRADUACOES = [
    "Gen Ex", "Gen Div", "Gen Bda", "Cel", "TC", "Maj", "Cap", 
    "1º Ten", "2º Ten", "Asp Of", "ST", "1º Sgt", "2º Sgt", 
    "3º Sgt", "Cb", "Sd", "SC"
]

# FUNÇÕES AUXILIARES PARA VISUALIZAÇÃO DE PDF E NC AUDITOR

def mostrar_visualizador_pdf(pdf_id, pdf_data):
    """Exibe um visualizador de PDF para o homologador - ATUALIZADA"""
    st.markdown("---")
    st.subheader("📄 VISUALIZAÇÃO DO DOCUMENTO")
    st.warning("⚠️ **OBRIGATÓRIO:** Visualize o documento completo antes de homologar!")
    
    # Caminho do arquivo PDF
    uploads_dir = "pdf_uploads"
    file_path = os.path.join(uploads_dir, f"{pdf_id}_{pdf_data['nome_arquivo']}")
    
    if os.path.exists(file_path):
        # Mostrar informações do documento
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**Arquivo:** {pdf_data['nome_arquivo']}")
            st.write(f"**Tamanho:** {os.path.getsize(file_path) / 1024:.1f} KB")
            st.write(f"**Status atual:** {pdf_data['status'].upper()}")
        with col2:
            st.write(f"**Tipo de Operação:** {'PREPARO' if pdf_data.get('tipo_operacao', '1') == '2' else 'EMPREGO'}")
            valor_operacao = pdf_data.get('valor_operacao', 0)
            if valor_operacao > 0:
                valor_formatado = f"R$ {valor_operacao:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                st.write(f"**Valor:** {valor_formatado}")
            if pdf_data.get('numero_ptrab'):
                st.write(f"**Nº P Trab:** {pdf_data['numero_ptrab']}")
        
        # Botão para abrir o PDF
        with open(file_path, "rb") as file:
            pdf_bytes = file.read()
        
        # Exibir PDF embed
        st.markdown("### 📋 Visualização do PDF")
        base64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
        pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="600" type="application/pdf"></iframe>'
        st.markdown(pdf_display, unsafe_allow_html=True)
        
        # Botão de download
        st.download_button(
            label="📥 BAIXAR PDF PARA ANÁLISE",
            data=pdf_bytes,
            file_name=pdf_data['nome_arquivo'],
            mime="application/pdf",
            use_container_width=True
        )
        
    else:
        st.error("❌ Arquivo PDF não encontrado no servidor.")
        st.info("📝 O arquivo pode ter sido movido ou excluído.")

def verificar_visualizacao_pdf(pdf_id):
    """Verifica se o PDF foi visualizado antes da homologação"""
    if f'pdf_viewed_{pdf_id}' not in st.session_state:
        st.session_state[f'pdf_viewed_{pdf_id}'] = False
    return st.session_state[f'pdf_viewed_{pdf_id}']

def abrir_planilha_nc_auditor():
    """Abre a planilha NC Auditor.xlsx usando o aplicativo padrão do sistema"""
    try:
        nc_auditor_file = 'nc_auditor.xlsx'
        
        if os.path.exists(nc_auditor_file):
            # Abrir o arquivo com o aplicativo padrão
            if os.name == 'nt':  # Windows
                os.startfile(nc_auditor_file)
            elif os.name == 'posix':  # Linux ou macOS
                import subprocess
                subprocess.run(['open', nc_auditor_file] if os.name == 'posix' and sys.platform == 'darwin' else ['xdg-open', nc_auditor_file])
            else:
                # Fallback para outros sistemas
                import webbrowser
                webbrowser.open(nc_auditor_file)
            
            return True
        else:
            st.error(f"❌ Arquivo {nc_auditor_file} não encontrado.")
            st.info("📝 A planilha será criada automaticamente quando o primeiro documento for aprovado.")
            return False
            
    except Exception as e:
        st.error(f"❌ Erro ao abrir a planilha: {e}")
        return False

def extrair_numero_ptrab_do_nome(nome_arquivo):
    """
    Extrai o número do P Trab do nome do arquivo PDF.
    Procura por padrões como 'P Trab Nr 00001/2024', 'PTrab00001/2024', etc.
    """
    try:
        # Padrões comuns para números de P Trab
        padroes = [
            r'P\s*Trab\s*Nr?\s*(\d+/\d+)',  # P Trab Nr 00001/2024
            r'PTrab\s*(\d+/\d+)',           # PTrab 00001/2024
            r'P_Trab_(\d+_\d+)',            # P_Trab_00001_2024
            r'P_Trab.*?(\d+[/_]\d+)',       # P_Trab_algumacoisa_00001/2024
            r'(\d{5}/\d{4})',               # 00001/2024 (padrão comum)
            r'(\d+/\d{4})',                 # 1/2024, 10/2024, etc.
        ]
        
        for padrao in padroes:
            match = re.search(padrao, nome_arquivo, re.IGNORECASE)
            if match:
                numero = match.group(1)
                # Formatar para o padrão correto
                if '/' in numero:
                    partes = numero.split('/')
                    if len(partes) == 2:
                        # Garantir que o número tenha 5 dígitos
                        num = partes[0].zfill(5)
                        ano = partes[1]
                        return f"P Trab Nr {num}/{ano}"
                elif '_' in numero:
                    partes = numero.split('_')
                    if len(partes) == 2:
                        num = partes[0].zfill(5)
                        ano = partes[1]
                        return f"P Trab Nr {num}/{ano}"
                
                return f"P Trab Nr {numero}"
        
        # Se não encontrou nenhum padrão, tentar extrair números sequenciais
        numeros = re.findall(r'\d+', nome_arquivo)
        if len(numeros) >= 2:
            # Assumir que os últimos dois números são o número e ano
            num = numeros[-2].zfill(5)
            ano = numeros[-1]
            if len(ano) == 4:  # Verificar se parece um ano
                return f"P Trab Nr {num}/{ano}"
        
        # Última tentativa: procurar qualquer número com 5 dígitos
        match = re.search(r'(\d{5})', nome_arquivo)
        if match:
            from datetime import datetime
            ano_atual = datetime.now().year
            return f"P Trab Nr {match.group(1)}/{ano_atual}"
            
        return None
        
    except Exception as e:
        print(f"Erro ao extrair número do P Trab: {e}")
        return None

# FUNÇÕES AUXILIARES PARA ALIMENTAÇÃO
def atualizar_dados_automaticos_auth(tipo_item, codom_selecionado, vinculacao_ativa):
    """Atualiza OM e CODUG automaticamente baseado no CODOM e tipo selecionados - CORRIGIDO"""
    if not CODOM_MANAGER_CARREGADO or not codom_selecionado or codom_selecionado == "Selecione o CODOM":
        return "", ""
    
    # Determinar tipo para busca no CODOM
    if "Ração Operacional" in tipo_item:
        # Para ração operacional, usar QR como base
        tipo_para_codom = 'QR'
    else:
        # Para QR/QS, usar o tipo exato
        tipo_para_codom = tipo_item
    
    # Obter SIGLA da OM - CORREÇÃO: sempre buscar a sigla específica
    sigla_om = codom_manager.get_sigla_for_tipo(codom_selecionado, tipo_para_codom)
    
    # Obter CODUG se vinculação estiver ativa
    codug = ""
    if vinculacao_ativa:
        codug = codom_manager.get_codug_for_tipo(codom_selecionado, tipo_para_codom)
    
    return sigla_om, codug

def calcular_racao_operacional(efetivo, dias, tipo_racao):
    """Calcula a quantidade de rações operacionais"""
    quantidade = efetivo * dias
    return quantidade, 0.00, 0.00  # quantidade, valor_unitario, valor_total

def gerar_descricao_racao_operacional(efetivo, dias, tipo_racao, nome_operacao):
    """Gera a descrição para ração operacional"""
    quantidade = efetivo * dias
    descricao = f"Fornecimento de {quantidade} rações operacionais {tipo_racao}, "
    descricao += f"com o objetivo de atender o efetivo de {efetivo} militares, "
    descricao += f"por {dias} dia(s), para consumo durante a Operação {nome_operacao}."
    return descricao

def gerar_calculo_racao_operacional(efetivo, dias, tipo_racao):
    """Gera o cálculo detalhado para ração operacional"""
    quantidade = efetivo * dias
    calculo = f"{efetivo} militares × {dias} dia(s) = {quantidade} rações operacionais"
    return calculo, quantidade

def gerar_calculo_detalhado_emprego(efetivo, dias_operacao, refeicoes_intermediarias, tipo):
    """Gera o cálculo detalhado formatado corretamente para EMPREGO - CORRIGIDO"""
    if tipo == 'QR':
        valor_etapa = 7.00
    else:  # QS
        valor_etapa = 10.00
        
    valor_ref_intr = valor_etapa / 3
    
    if dias_operacao <= 22:
        total = efetivo * refeicoes_intermediarias * valor_ref_intr * dias_operacao
        calculo_detalhado = f"{efetivo} militares × {refeicoes_intermediarias} Ref Itr × (R$ {valor_etapa:.2f} ÷ 3) × {dias_operacao} dias = R$ {total:.2f}"
        
    else:
        dias_ate_22 = 22
        dias_apos_22 = min(dias_operacao - 22, 8)
        
        if dias_operacao <= 30:
            parte1 = efetivo * refeicoes_intermediarias * valor_ref_intr * dias_ate_22
            parte2 = efetivo * valor_etapa * dias_apos_22
            total = parte1 + parte2
            
            calculo_detalhado = f"PRIMEIROS 22 DIAS: {efetivo} × {refeicoes_intermediarias} × R$ {valor_ref_intr:.2f} × {dias_ate_22} = R$ {parte1:.2f}\n"
            calculo_detalhado += f"DIAS 23-30: {efetivo} × R$ {valor_etapa:.2f} × {dias_apos_22} = R$ {parte2:.2f}\n"
            calculo_detalhado += f"TOTAL: R$ {parte1:.2f} + R$ {parte2:.2f} = R$ {total:.2f}"
            
        else:
            # Operação com mais de 30 dias (múltiplos períodos)
            # Primeiro período: 30 dias (22 + 8)
            valor_primeiro_periodo = (efetivo * refeicoes_intermediarias * valor_ref_intr * 22 +
                                    efetivo * valor_etapa * 8)
            
            # Períodos adicionais completos de 30 dias
            dias_excedentes = dias_operacao - 30
            periodos_completos = dias_excedentes // 30
            dias_restantes = dias_excedentes % 30
            
            valor_periodos_completos = 0
            if periodos_completos > 0:
                valor_periodo_completo = (efetivo * refeicoes_intermediarias * valor_ref_intr * 22 +
                                        efetivo * valor_etapa * 8)
                valor_periodos_completos = valor_periodo_completo * periodos_completos
            
            # Período parcial restante
            valor_periodo_parcial = 0
            if dias_restantes > 0:
                dias_ate_22_parcial = min(dias_restantes, 22)
                dias_apos_22_parcial = min(max(dias_restantes - 22, 0), 8)
                
                valor_periodo_parcial = (efetivo * refeicoes_intermediarias * valor_ref_intr * dias_ate_22_parcial +
                                       efetivo * valor_etapa * dias_apos_22_parcial)
            
            total = valor_primeiro_periodo + valor_periodos_completos + valor_periodo_parcial
            
            calculo_detalhado = f"PRIMEIROS 30 DIAS: [({efetivo} × {refeicoes_intermediarias} × R$ {valor_ref_intr:.2f} × 22 dias) + ({efetivo} × R$ {valor_etapa:.2f} × 8 dias)] = R$ {valor_primeiro_periodo:.2f}"
            
            if periodos_completos > 0:
                calculo_detalhado += f"\n{periodos_completos} PERÍODO(S) COMPLETO(S) DE 30 DIAS: [({efetivo} × {refeicoes_intermediarias} × R$ {valor_ref_intr:.2f} × 22 dias) + ({efetivo} × R$ {valor_etapa:.2f} × 8 dias)] × {periodos_completos} = R$ {valor_periodos_completos:.2f}"
            
            if dias_restantes > 0:
                calculo_detalhado += f"\nPERÍODO PARCIAL DE {dias_restantes} DIAS: [({efetivo} × {refeicoes_intermediarias} × R$ {valor_ref_intr:.2f} × {dias_ate_22_parcial} dias) + ({efetivo} × R$ {valor_etapa:.2f} × {dias_apos_22_parcial} dias)] = R$ {valor_periodo_parcial:.2f}"
            
            calculo_detalhado += f"\nTOTAL GERAL: R$ {valor_primeiro_periodo:.2f} + R$ {valor_periodos_completos:.2f} + R$ {valor_periodo_parcial:.2f} = R$ {total:.2f}"

    return calculo_detalhado

def gerar_calculo_detalhado_preparo(efetivo, dias_operacao, tipo):
    """Gera o cálculo detalhado para operações de PREPARO com limite de 8 dias - CORRIGIDO"""
    if tipo == 'QR':
        valor_etapa_especifica = 7.00  # QR
        valor_complemento_especifico = 1.40  # 20% de R$6,00
    else:  # QS
        valor_etapa_especifica = 10.00  # QS
        valor_complemento_especifico = 2.00  # 20% de R$9,00
    
    if dias_operacao <= 22:
        total = efetivo * valor_complemento_especifico * dias_operacao
        calculo_detalhado = f"{efetivo} militares × R$ {valor_complemento_especifico:.2f} × {dias_operacao} dias = R$ {total:.2f}"
        
    else:
        dias_ate_22 = 22
        dias_apos_22 = min(dias_operacao - 22, 8)
        
        if dias_operacao <= 30:
            parte1 = efetivo * valor_complemento_especifico * dias_ate_22
            parte2 = efetivo * valor_etapa_especifica * dias_apos_22
            parte3 = efetivo * valor_complemento_especifico * dias_apos_22
            total = parte1 + parte2 + parte3
            
            calculo_detalhado = f"PRIMEIROS 22 DIAS: {efetivo} × R$ {valor_complemento_especifico:.2f} × {dias_ate_22} = R$ {parte1:.2f}\n"
            calculo_detalhado += f"DIAS 23-30: {efetivo} × R$ {valor_etapa_especifica:.2f} × {dias_apos_22} = R$ {parte2:.2f}\n"
            calculo_detalhado += f"DIAS 23-30 (Complemento): {efetivo} × R$ {valor_complemento_especifico:.2f} × {dias_apos_22} = R$ {parte3:.2f}\n"
            calculo_detalhado += f"TOTAL: R$ {parte1:.2f} + R$ {parte2:.2f} + R$ {parte3:.2f} = R$ {total:.2f}"
            
        else:
            # Operação com mais de 30 dias (múltiplos períodos)
            # Primeiro período: 30 dias (22 + 8)
            valor_primeiro_periodo = (efetivo * valor_complemento_especifico * 22 +
                                    efetivo * valor_etapa_especifica * 8 +
                                    efetivo * valor_complemento_especifico * 8)
            
            # Períodos adicionais completos de 30 dias
            dias_excedentes = dias_operacao - 30
            periodos_completos = dias_excedentes // 30
            dias_restantes = dias_excedentes % 30
            
            valor_periodos_completos = 0
            if periodos_completos > 0:
                valor_periodo_completo = (efetivo * valor_complemento_especifico * 22 +
                                        efetivo * valor_etapa_especifica * 8 +
                                        efetivo * valor_complemento_especifico * 8)
                valor_periodos_completos = valor_periodo_completo * periodos_completos
            
            # Período parcial restante
            valor_periodo_parcial = 0
            if dias_restantes > 0:
                dias_ate_22_parcial = min(dias_restantes, 22)
                dias_apos_22_parcial = min(max(dias_restantes - 22, 0), 8)
                
                valor_periodo_parcial = (efetivo * valor_complemento_especifico * dias_ate_22_parcial +
                                       efetivo * valor_etapa_especifica * dias_apos_22_parcial +
                                       efetivo * valor_complemento_especifico * dias_apos_22_parcial)
            
            total = valor_primeiro_periodo + valor_periodos_completos + valor_periodo_parcial
            
            calculo_detalhado = f"PRIMEIROS 30 DIAS: [({efetivo} × R$ {valor_complemento_especifico:.2f} × 22 dias) + ({efetivo} × R$ {valor_etapa_especifica:.2f} × 8 dias) + ({efetivo} × R$ {valor_complemento_especifico:.2f} × 8 dias)] = R$ {valor_primeiro_periodo:.2f}"
            
            if periodos_completos > 0:
                calculo_detalhado += f"\n{periodos_completos} PERÍODO(S) COMPLETO(S) DE 30 DIAS: [({efetivo} × R$ {valor_complemento_especifico:.2f} × 22 dias) + ({efetivo} × R$ {valor_etapa_especifica:.2f} × 8 dias) + ({efetivo} × R$ {valor_complemento_especifico:.2f} × 8 dias)] × {periodos_completos} = R$ {valor_periodos_completos:.2f}"
            
            if dias_restantes > 0:
                calculo_detalhado += f"\nPERÍODO PARCIAL DE {dias_restantes} DIAS: [({efetivo} × R$ {valor_complemento_especifico:.2f} × {dias_ate_22_parcial} dias) + ({efetivo} × R$ {valor_etapa_especifica:.2f} × {dias_apos_22_parcial} dias) + ({efetivo} × R$ {valor_complemento_especifico:.2f} × {dias_apos_22_parcial} dias)] = R$ {valor_periodo_parcial:.2f}"
            
            calculo_detalhado += f"\nTOTAL GERAL: R$ {valor_primeiro_periodo:.2f} + R$ {valor_periodos_completos:.2f} + R$ {valor_periodo_parcial:.2f} = R$ {total:.2f}"
    
    return calculo_detalhado

def criar_pdf_real(dados_cabecalho, dados_operacao, itens_alimentacao, dados_assinatura, nome_arquivo, numero_controle):
    """Cria o PDF real usando reportlab COM FORMATAÇÃO DETALHADA - CORRIGIDO"""
    try:
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
        from reportlab.lib.units import mm
        
        # Usar o gerador do módulo operacional para garantir formatação consistente
        gerador = GeradorPDFPTrab()
        
        # Configurar documento
        doc = SimpleDocTemplate(
            nome_arquivo,
            pagesize=landscape(A4),
            rightMargin=20*mm,
            leftMargin=20*mm,
            topMargin=20*mm,
            bottomMargin=20*mm
        )
        
        story = []
        
        # Cabeçalho com brasão (usando função do módulo operacional)
        story.extend(gerador.criar_cabecalho_com_brasao(dados_cabecalho, numero_controle))
        story.append(Spacer(1, 5*mm))
        
        # Informações da operação
        story.append(gerador.criar_info_operacao(dados_operacao))
        story.append(Spacer(1, 5*mm))
        
        # Processar itens para o formato correto
        itens_processados = []
        for item in itens_alimentacao:
            # CORREÇÃO CRÍTICA: Obter a sigla CORRETA baseada no tipo (QR/QS) para a coluna OM (UGE) CODUG
            if CODOM_MANAGER_CARREGADO:
                # Usar a sigla específica para o tipo selecionado - ESTA É A SIGLA QUE VAI NA COLUNA OM (UGE) CODUG
                sigla_para_codug = codom_manager.get_sigla_for_tipo(item['codom'], item['tipo'])
                
                # Para a coluna CODOM, usar a descrição completa
                codom_completo = codom_manager.get_descricao_completa(item['codom'])
            else:
                sigla_para_codug = item['om']
                codom_completo = f"{item['codom']} - {item['om']}"
            
            print(f"🔍 DEBUG PDF - Item: {item['tipo']}")
            print(f"   CODOM: {item['codom']}")
            print(f"   SIGLA para CODUG: {sigla_para_codug}")
            print(f"   CODUG: {item['codug']}")
            print(f"   Coluna OM (UGE) CODUG: {sigla_para_codug} ({item['codug']})")
            
            # Converter para formato compatível com a tabela detalhada
            if item.get('eh_racao_operacional', False):
                # Ração operacional
                finalidade = f"Rção Operacional ({item.get('tipo_racao', 'R2')})"
                
                item_formatado = {
                    'odop_ods': 'COLOG',
                    'gnd': '3',
                    'ed': '30',
                    'finalidade': finalidade,
                    'om_uge_codug': f"{sigla_para_codug} ({item['codug']})",  # CORREÇÃO: Usar sigla do CODUG
                    'codom': codom_completo,  # CODOM com descrição completa
                    'quantidade_base': item['efetivo'],
                    'unidade_base': 'Ração/dia',
                    'valor_unitario': 0.00,
                    'quantidade_dias': item['dias'],
                    'valor_total': 0.00,
                    'natureza_despesa': f'33.90.30 - Aquisição de rações operacionais ({item.get("tipo_racao", "R2")})',
                    'descricao_memoria': f'destinada ao fornecimento de rações operacionais {item.get("tipo_racao", "R2")} para {item["efetivo"]} militares durante {item["dias"]} dias',
                    'formula': f"Fórmula: Efetivo × Nº de dias = Quantidade total de rações",
                    'calculo_detalhado': f"{item['efetivo']} militares × {item['dias']} dias = {item['efetivo'] * item['dias']} rações operacionais",
                    'total_item': f'TOTAL {item.get("tipo_racao", "R2")}: {item["efetivo"] * item["dias"]} rações operacionais (valor: R$ 0,00)'
                }
            else:
                # QR/QS
                if dados_operacao['tipo'] == '1':  # EMPREGO
                    valor_total, valor_unitario = gerador.calcular_valores_emprego(
                        item['efetivo'],
                        item['dias'],
                        item['refeicoes_intermediarias'], 
                        item['tipo']
                    )
                    calculo_detalhado = gerar_calculo_detalhado_emprego(
                        item['efetivo'],
                        item['dias'],
                        item['refeicoes_intermediarias'],
                        item['tipo']
                    )
                    
                    if item['dias'] <= 22:
                        formula = 'Fórmula: Efetivo empregado x nº Ref Itr (máximo de 03) x Valor da etapa/3 x Nr de dias'
                    else:
                        formula = 'Fórmula: Efetivo empregado x nº Ref Itr (máximo de 03) x Valor da etapa/3 x 22 dias + Efetivo empregado x Valor da etapa x Nr dias após 22 (até 8 dias)'
                    
                    num_refeicoes = item['refeicoes_intermediarias']
                    if num_refeicoes == 1:
                        texto_refeicoes = 'para 01 (uma) refeição intermediária'
                    elif num_refeicoes == 2:
                        texto_refeicoes = 'para 02 (duas) refeições intermediárias'
                    else:
                        texto_refeicoes = 'para 03 (três) refeições intermediárias'
                    
                else:  # PREPARO
                    valor_total, valor_unitario = gerador.calcular_valores_preparo(
                        item['efetivo'],
                        item['dias'],
                        item['tipo']
                    )
                    calculo_detalhado = gerar_calculo_detalhado_preparo(
                        item['efetivo'],
                        item['dias'],
                        item['tipo']
                    )
                    
                    if item['dias'] <= 22:
                        formula = 'Fórmula: Efetivo empregado x Complemento de Operação (20%) x Nr de dias até 22 dias'
                    else:
                        formula = 'Fórmula: Efetivo empregado x Complemento de Operação (20%) x 22 dias + Efetivo empregado x Valor da etapa x Nr dias após 22 (até 8 dias) + Efetivo empregado x Complemento de Operação (20%) x Nr dias após 22 (até 8 dias)'

                valor_total_formatado = gerador.formatar_moeda(valor_total)
                
                # Formatar cálculo detalhado
                calculo_detalhado_formatado = calculo_detalhado
                valores = re.findall(r'R\$\s*(\d+\.?\d*)', calculo_detalhado)
                for valor in valores:
                    try:
                        valor_float = float(valor)
                        valor_formatado = gerador.formatar_moeda(valor_float)
                        calculo_detalhado_formatado = calculo_detalhado_formatado.replace(f"R$ {valor}", valor_formatado)
                    except:
                        pass

                item_formatado = {
                    'odop_ods': 'COLOG',
                    'gnd': '3',
                    'ed': '30',
                    'finalidade': f"{'Subsistência' if item['tipo'] == 'QS' else 'Rancho'} ({item['tipo']})",
                    'om_uge_codug': f"{sigla_para_codug} ({item['codug']})",  # CORREÇÃO CRÍTICA: Usar sigla do CODUG
                    'codom': codom_completo,  # CODOM com descrição completa
                    'quantidade_base': item['efetivo'],
                    'unidade_base': 'H/dia',
                    'valor_unitario': valor_unitario,
                    'quantidade_dias': item['dias'],
                    'valor_total': valor_total,
                    'natureza_despesa': f'33.90.30 - Aquisição de gêneros alimentícios ({item["tipo"]}) {texto_refeicoes if dados_operacao["tipo"] == "1" else ""}',
                    'descricao_memoria': f'destinada à complementação de alimentação de {item["efetivo"]} militares durante {item["dias"]} dias',
                    'formula': formula,
                    'calculo_detalhado': calculo_detalhado_formatado,
                    'total_item': f'TOTAL {item["tipo"]}: {valor_total_formatado}'
                }
            
            itens_processados.append(item_formatado)
        
        # Tabela de alimentação (usando função do módulo operacional)
        items_por_pagina = 5
        total_itens = len(itens_processados)
        
        for i in range(0, total_itens, items_por_pagina):
            if i > 0:
                story.append(PageBreak())
                story.extend(gerador.criar_cabecalho_com_brasao(dados_cabecalho, numero_controle))
                story.append(Spacer(1, 5*mm))
            
            itens_pagina = itens_processados[i:i + items_por_pagina]
            tabela_pagina = gerador.criar_tabela_alimentacao(itens_pagina)
            story.append(tabela_pagina)
        
        # Rodapé
        story.append(Spacer(1, 10*mm))
        story.append(gerador.criar_rodape(
            dados_assinatura['local'], 
            dados_assinatura['militar'], 
            dados_assinatura['funcao']
        ))
        
        # Gerar PDF
        doc.build(story)
        return True
        
    except Exception as e:
        st.error(f"Erro ao criar PDF: {str(e)}")
        import traceback
        st.error(f"Detalhes do erro: {traceback.format_exc()}")
        return False

# Função para carregar OMs do CODOM
def carregar_oms_do_codom():
    """Carrega a lista de OMs do arquivo CODOM.xlsx com formato CODOM - Descrição"""
    oms = []
    
    if CODOM_MANAGER_CARREGADO and hasattr(codom_manager, 'codom_data'):
        for codom, dados in codom_manager.codom_data.items():
            descricao = dados.get('descricao', '')
            
            # Usar formato: CODOM - Descrição (ao invés de sigla)
            display_text = f"{codom} - {descricao}"
            oms.append(display_text)
        
        # Ordenar por CODOM
        oms.sort()
    else:
        # Fallback caso o CODOM não esteja carregado
        oms = [
            "6122 - 40º BI",
            "1503 - 23º BC", 
            "1438 - Ba Adm / Gu Fortaleza"
        ]
    
    return oms

# Função para pesquisar OMs
def pesquisar_oms(termo, lista_oms):
    """Pesquisa OMs por CODOM ou descrição"""
    if not termo:
        return lista_oms
    
    termo = termo.lower().strip()
    resultados = []
    
    for om in lista_oms:
        if termo in om.lower():
            resultados.append(om)
    
    return resultados if resultados else ["Nenhuma OM encontrada"]

# FUNÇÕES PRINCIPAIS DAS ABAS

def show_login_page():
    """Exibe a página de login"""
    st.markdown('<div class="login-container">', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if os.path.exists('colog.png'):
            st.image('colog.png', width=100)
        else:
            st.markdown('<div style="font-size: 3rem; text-align: center;">🔐</div>', unsafe_allow_html=True)
    
    st.markdown('<h2 style="text-align: center; color: #000000;">SISTEMA DE PLANO DE TRABALHO LOGÍSTICO</h2>', unsafe_allow_html=True)
    st.markdown('<h3 style="text-align: center; color: #2e5cb8;">ACESSO RESTRITO</h3>', unsafe_allow_html=True)
    
    # Verificar se deve mostrar a tela de recuperação de senha
    if st.session_state.get('show_forgot_password', False):
        show_forgot_password()
        return
    
    with st.form("login_form"):
        cpf = st.text_input("**CPF:**", placeholder="Digite seu CPF (apenas números)", value="")
        password = st.text_input("**Senha:**", type="password", placeholder="Digite sua senha", value="")
        
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            login_submitted = st.form_submit_button("🚪 ENTRAR", use_container_width=True)
        with col_btn2:
            forgot_password = st.form_submit_button("🔓 ESQUECI MINHA SENHA", use_container_width=True)
    
    if login_submitted:
        if cpf and password:
            success, result = auth_system.login(cpf, password)
            if success:
                st.session_state['logged_in'] = True
                st.session_state['user_info'] = result
                st.success(f"✅ Login realizado com sucesso! Bem-vindo, {result['nome']}")
                st.rerun()
            else:
                st.error(f"❌ {result}")
        else:
            st.error("❌ Preencha CPF e senha")
    
    if forgot_password:
        st.session_state.show_forgot_password = True
        st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)

def show_forgot_password():
    """Exibe o formulário de recuperação de senha"""
    st.markdown('<div class="login-container">', unsafe_allow_html=True)
    
    st.markdown('<h3 style="text-align: center; color: #2e5cb8;">🔓 RECUPERAÇÃO DE SENHA</h3>', unsafe_allow_html=True)
    
    with st.form("forgot_password_form"):
        cpf = st.text_input("**CPF:**", placeholder="Digite seu CPF (apenas números)")
        email = st.text_input("**E-mail:**", placeholder="Digite o e-mail cadastrado")
        
        if st.form_submit_button("🔑 ENVIAR NOVA SENHA", use_container_width=True):
            if cpf and email:
                cpf_clean = re.sub(r'\D', '', cpf)
                
                # Verificar se o CPF e email correspondem
                if cpf_clean in auth_system.users:
                    user = auth_system.users[cpf_clean]
                    if user['email'].lower() == email.lower():
                        # Gerar senha temporária
                        temp_password = auth_system.generate_temporary_password()
                        
                        # Atualizar senha no sistema
                        auth_system.users[cpf_clean]['password'] = auth_system.hash_password(temp_password)
                        auth_system.save_users()
                        
                        # Enviar email
                        success, message = auth_system.send_password_reset_email(cpf_clean, temp_password)
                        
                        if success:
                            st.success(f"✅ {message}")
                            st.info("⚠️ Por segurança, altere sua senha após o primeiro acesso.")
                        else:
                            st.error(f"❌ {message}")
                    else:
                        st.error("❌ E-mail não corresponde ao cadastrado para este CPF")
                else:
                    st.error("❌ CPF não encontrado")
            else:
                st.error("❌ Preencha CPF e e-mail")
    
    if st.button("⬅️ VOLTAR AO LOGIN"):
        st.session_state.show_forgot_password = False
        st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)

def show_change_password():
    """Exibe o formulário para alteração de senha"""
    st.markdown('<div class="section-header">🔐 ALTERAR SENHA</div>', unsafe_allow_html=True)
    
    with st.form("change_password_form"):
        st.write("**Alteração de Senha**")
        
        current_password = st.text_input("**Senha Atual:**", type="password", placeholder="Digite sua senha atual")
        new_password = st.text_input("**Nova Senha:**", type="password", placeholder="Digite a nova senha")
        confirm_password = st.text_input("**Confirmar Nova Senha:**", type="password", placeholder="Confirme a nova senha")
        
        if st.form_submit_button("🔄 ALTERAR SENHA", use_container_width=True):
            if not current_password or not new_password or not confirm_password:
                st.error("❌ Todos os campos são obrigatórios")
            elif new_password != confirm_password:
                st.error("❌ As senhas não coincidem")
            else:
                # Encontrar o CPF do usuário atual
                user_cpf = None
                for cpf, user in auth_system.users.items():
                    if user['nome'] == st.session_state.user_info['nome']:
                        user_cpf = cpf
                        break
                
                if user_cpf:
                    success, message = auth_system.change_password(user_cpf, current_password, new_password)
                    if success:
                        st.success(f"✅ {message}")
                    else:
                        st.error(f"❌ {message}")
                else:
                    st.error("❌ Não foi possível encontrar seu usuário")

def show_user_registration():
    """Exibe o formulário de cadastro de usuários aprimorado"""
    st.markdown('<div class="section-header">📋 CADASTRO DE USUÁRIOS</div>', unsafe_allow_html=True)
    
    # Verificar se o usuário tem permissão
    user_perfil = st.session_state.user_info['perfil']
    if user_perfil not in ['cadastrador', 'master']:
        st.error("❌ Acesso não autorizado. Esta funcionalidade requer perfil de cadastrador ou master.")
        return
    
    # Carregar lista de OMs
    lista_oms = carregar_oms_do_codom()
    
    with st.form("user_registration_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            nome = st.text_input("**Nome Completo:**", placeholder="Digite o nome completo")
            posto = st.selectbox("**Posto/Graduação:**", options=POSTOS_GRADUACOES, index=3)
            
            # CAMPO OM COM PESQUISA
            st.markdown("**Organização Militar:**")
            
            # Campo de pesquisa
            pesquisa_om = st.text_input("🔍 Pesquisar OM:", placeholder="Digite CODOM ou nome da OM...", 
                                      key="pesquisa_om")
            
            # Filtrar OMs baseado na pesquisa
            if pesquisa_om:
                oms_filtradas = pesquisar_oms(pesquisa_om, lista_oms)
                if oms_filtradas == ["Nenhuma OM encontrada"]:
                    st.warning("Nenhuma OM encontrada. Mostrando todas as opções.")
                    oms_para_select = lista_oms
                else:
                    oms_para_select = oms_filtradas
            else:
                oms_para_select = lista_oms
            
            # Selectbox com opções filtradas
            om = st.selectbox("Selecione a OM:", options=oms_para_select, 
                            index=0, key="select_om",
                            help="Use o campo de pesquisa acima para filtrar")
        
        with col2:
            cpf = st.text_input("**CPF:**", placeholder="Apenas números (11 dígitos)", max_chars=11)
            email = st.text_input("**E-mail:**", placeholder="email@exemplo.com")
            
            # CORREÇÃO: Master pode cadastrar todos os perfis, cadastrador apenas usuário e cadastrador
            if st.session_state.user_info['perfil'] == 'master':
                perfil = st.selectbox("**Perfil:**", ["usuário", "cadastrador", "homologador", "master"])
            else:
                perfil = st.selectbox("**Perfil:**", ["usuário", "cadastrador"])
            
            password = st.text_input("**Senha:**", type="password", placeholder="Mínimo 6 caracteres com letras, números e símbolo")
        
        col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
        with col_btn2:
            cadastrar_submit = st.form_submit_button("✅ CADASTRAR USUÁRIO", use_container_width=True)
        
        if cadastrar_submit:
            errors = []
            
            if not nome.strip():
                errors.append("Nome completo é obrigatório")
            
            if not cpf.strip():
                errors.append("CPF é obrigatório")
            elif len(cpf) != 11 or not cpf.isdigit():
                errors.append("CPF deve conter exatamente 11 dígitos numéricos")
            
            if not email.strip():
                errors.append("E-mail é obrigatório")
            elif not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
                errors.append("E-mail inválido")
            
            if not password:
                errors.append("Senha é obrigatória")
            else:
                is_valid_pass, msg_pass = auth_system.validate_password(password)
                if not is_valid_pass:
                    errors.append(f"Senha: {msg_pass}")
            
            if errors:
                for error in errors:
                    st.error(f"❌ {error}")
            else:
                nome_upper = nome.upper()
                success, message = auth_system.register_user(
                    nome_upper, posto, om, cpf, email, password, perfil,
                    st.session_state.user_info['nome']
                )
                if success:
                    st.success(f"✅ {message}")
                else:
                    st.error(f"❌ {message}")

def show_users_management():
    """Exibe a gestão completa de usuários (apenas para master) - CORRIGIDO"""
    st.markdown('<div class="section-header">👥 GESTÃO DE USUÁRIOS</div>', unsafe_allow_html=True)
    
    # Verificar se é master
    if st.session_state.user_info['perfil'] != 'master':
        st.error("❌ Acesso não autorizado. Esta funcionalidade requer perfil master.")
        return
    
    # DEBUG: Verificar se o sistema de autenticação está carregado
    st.write("🔍 DEBUG: Verificando sistema de autenticação...")
    
    # Verificar se existem usuários carregados
    if not hasattr(auth_system, 'users') or auth_system.users is None:
        st.error("❌ Sistema de autenticação não foi carregado corretamente.")
        st.info("📝 Tentando recarregar usuários...")
        try:
            auth_system.load_users()
            st.success("✅ Usuários recarregados com sucesso!")
        except Exception as e:
            st.error(f"❌ Erro ao recarregar usuários: {e}")
            return
    
    if not auth_system.users:
        st.error("❌ Nenhum usuário encontrado no sistema.")
        st.info("📝 O arquivo de usuários pode estar vazio ou corrompido.")
        return
    
    st.success(f"✅ Sistema carregado com {len(auth_system.users)} usuário(s)")
    
    # Filtro por OM
    st.subheader("🔍 Filtrar por Organização Militar")
    om_filter = st.text_input("Digite o nome ou CODOM da OM:", placeholder="Ex: 40º BI ou 6122", key="om_filter_users")
    
    # Carregar usuários filtrados
    if om_filter:
        users_data = auth_system.get_users_by_om(om_filter)
        st.info(f"Mostrando {len(users_data)} usuário(s) para: '{om_filter}'")
    else:
        users_data = auth_system.users
        st.info(f"Mostrando todos os {len(users_data)} usuário(s)")
    
    if users_data:
        # Converter para DataFrame para exibição
        users_list = []
        for cpf, user in users_data.items():
            users_list.append({
                'CPF': cpf,
                'Nome': user.get('nome', 'N/A'),
                'Posto': user.get('posto', 'N/A'),
                'OM': user.get('om', 'N/A'),
                'E-mail': user.get('email', 'N/A'),
                'Perfil': user.get('perfil', 'N/A'),
                'Status': 'Ativo' if user.get('ativo', True) else 'Inativo',
                'Data Cadastro': user.get('data_cadastro', 'N/A')[:10] if user.get('data_cadastro') else 'N/A',
                'Cadastrado por': user.get('cadastrado_por', 'N/A')
            })
        
        df = pd.DataFrame(users_list)
        st.dataframe(df, use_container_width=True)
        
        # Gestão de usuários
        st.subheader("⚙️ Gerenciar Usuário")
        col1, col2 = st.columns(2)
        
        with col1:
            cpf_to_manage = st.text_input("CPF do usuário para gerenciar:", placeholder="Digite o CPF (apenas números)", key="cpf_to_manage")
        
        with col2:
            action = st.selectbox("Ação:", ["Selecione...", "Editar", "Excluir", "Ativar/Desativar"], key="action_select")
        
        if cpf_to_manage and cpf_to_manage in users_data and action != "Selecione...":
            user_to_manage = users_data[cpf_to_manage]
            st.info(f"Usuário selecionado: {user_to_manage.get('nome', 'N/A')} - {user_to_manage.get('posto', 'N/A')}")
            
            if action == "Editar":
                with st.form("edit_user_form"):
                    col1, col2 = st.columns(2)
                    with col1:
                        new_nome = st.text_input("Nome:", value=user_to_manage.get('nome', ''), key="edit_nome")
                        new_posto = st.selectbox("Posto:", options=POSTOS_GRADUACOES, 
                                               index=POSTOS_GRADUACOES.index(user_to_manage.get('posto', 'CEL')) if user_to_manage.get('posto') in POSTOS_GRADUACOES else 3, 
                                               key="edit_posto")
                        new_om = st.text_input("OM:", value=user_to_manage.get('om', ''), key="edit_om")
                    with col2:
                        new_email = st.text_input("E-mail:", value=user_to_manage.get('email', ''), key="edit_email")
                        new_perfil = st.selectbox("Perfil:", ["usuário", "cadastrador", "homologador", "master"],
                                                index=["usuário", "cadastrador", "homologador", "master"].index(user_to_manage.get('perfil', 'usuário')) if user_to_manage.get('perfil') in ["usuário", "cadastrador", "homologador", "master"] else 0,
                                                key="edit_perfil")
                    
                    if st.form_submit_button("💾 SALVAR ALTERAÇÕES", key="save_edit"):
                        updates = {
                            'nome': new_nome,
                            'posto': new_posto,
                            'om': new_om,
                            'email': new_email,
                            'perfil': new_perfil
                        }
                        success, message = auth_system.update_user(cpf_to_manage, updates)
                        if success:
                            st.success(f"✅ {message}")
                            st.rerun()
                        else:
                            st.error(f"❌ {message}")
            
            elif action == "Excluir":
                st.warning(f"⚠️ ATENÇÃO: Esta ação excluirá permanentemente o usuário {user_to_manage.get('nome', 'N/A')}!")
                if st.button("🗑️ CONFIRMAR EXCLUSÃO", type="secondary", key="confirm_delete"):
                    success, message = auth_system.delete_user(cpf_to_manage)
                    if success:
                        st.success(f"✅ {message}")
                        st.rerun()
                    else:
                        st.error(f"❌ {message}")
            
            elif action == "Ativar/Desativar":
                new_status = not user_to_manage.get('ativo', True)
                status_text = "ativar" if new_status else "desativar"
                st.warning(f"⚠️ Confirmar {status_text} usuário {user_to_manage.get('nome', 'N/A')}?")
                if st.button(f"🔄 CONFIRMAR {status_text.upper()}", key=f"confirm_{status_text}"):
                    success, message = auth_system.update_user(cpf_to_manage, {'ativo': new_status})
                    if success:
                        st.success(f"✅ {message}")
                        st.rerun()
                    else:
                        st.error(f"❌ {message}")
        elif cpf_to_manage and action != "Selecione...":
            st.error("❌ CPF não encontrado na lista de usuários")
    else:
        st.info("📝 Nenhum usuário encontrado com os filtros aplicados.")

def show_homologacao_tab():
    """Exibe a aba de homologação COTER com gerenciamento de saldo - ATUALIZADA COM EXTRACTION AUTOMÁTICA DO P TRAB"""
    
    # Verificar se o sistema de homologação está carregado
    if not HOMOLOGACAO_SYSTEM_CARREGADO:
        st.error("❌ Sistema de homologação não está carregado. Não é possível acessar esta funcionalidade.")
        return
    
    # Verificar se o usuário tem permissão
    user_perfil = st.session_state.user_info['perfil']
    if user_perfil not in ['homologador', 'master']:
        st.error("❌ Acesso não autorizado. Esta funcionalidade requer perfil de homologador ou master.")
        return
    
    st.markdown('<div class="section-header">📄 HOMOLOGAÇÃO COTER</div>', unsafe_allow_html=True)
    
    # Card de Saldo
    if SALDO_MANAGER_CARREGADO:
        saldo_atual = saldo_manager.get_saldo_atual()
        saldo_formatado = saldo_manager.get_saldo_formatado()
        
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            st.markdown(f"""
            <div class="saldo-card">
                <h3 style="color: #155724; margin: 0;">💰 Saldo Preparo 2026</h3>
                <h1 style="color: #155724; margin: 10px 0; font-size: 2.5rem;">{saldo_formatado}</h1>
                <p style="color: #155724; margin: 0;">Saldo disponível para operações de preparo</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            # Botão para ver extrato
            if st.button("📊 Ver Extrato", use_container_width=True):
                st.session_state.show_extrato = True
        
        with col3:
            # Botão para resetar saldo (apenas master)
            if user_perfil == 'master':
                if st.button("🔄 Resetar Saldo", use_container_width=True, type="secondary"):
                    if st.checkbox("Confirmar reset do saldo?"):
                        success, msg = saldo_manager.resetar_saldo(st.session_state.user_info['nome'])
                        if success:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)
    
    # BOTÃO PARA ABRIR PLANILHA NC AUDITOR (apenas master)
    if user_perfil == 'master':
        st.markdown("---")
        col_nc1, col_nc2, col_nc3 = st.columns([1, 2, 1])
        with col_nc2:
            if st.button("📊 ABRIR PLANILHA NC AUDITOR", use_container_width=True, type="primary"):
                if abrir_planilha_nc_auditor():
                    st.success("✅ Planilha NC Auditor aberta com sucesso!")
                else:
                    st.error("❌ Erro ao abrir a planilha NC Auditor")
        st.markdown("---")
    
    tab1, tab2, tab3, tab4 = st.tabs(["⏳ PENDENTES", "✅ APROVADOS", "❌ REJEITADOS", "📊 EXTRATO"])
    
    with tab1:
        st.subheader("📋 Documentos Pendentes de Homologação")
        pdfs_pendentes = homologacao_system.get_pdfs_pendentes()
        
        if pdfs_pendentes:
            for pdf_id, pdf_data in pdfs_pendentes.items():
                with st.expander(f"📄 {pdf_data['nome_arquivo']} - {pdf_data['usuario']} ({pdf_data['posto_usuario']})", expanded=False):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**Upload em:** {pdf_data['data_upload'][:16]}")
                        st.write(f"**Usuário:** {pdf_data['usuario']} ({pdf_data['posto_usuario']})")
                        st.write(f"**OM:** {pdf_data['om_usuario']}")
                        tipo_operacao = pdf_data.get('tipo_operacao', '1')
                        st.write(f"**Tipo:** {'PREPARO' if tipo_operacao == '2' else 'EMPREGO'}")
                    with col2:
                        st.write(f"**Operação:** {pdf_data['dados_operacao'].get('nome_operacao', 'N/A')}")
                        st.write(f"**Período:** {pdf_data['dados_operacao'].get('periodo', 'N/A')}")
                        st.write(f"**Efetivo:** {pdf_data['dados_operacao'].get('efetivo_total', 'N/A')}")
                        valor_operacao = pdf_data.get('valor_operacao', 0)
                        if valor_operacao > 0:
                            valor_formatado = f"R$ {valor_operacao:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                            st.write(f"**Valor:** {valor_formatado}")
                    
                    # Verificar saldo para operações de preparo
                    tipo_operacao = pdf_data.get('tipo_operacao', '1')  # Default para EMPREGO se não existir
                    if tipo_operacao == '2' and SALDO_MANAGER_CARREGADO:
                        if valor_operacao > saldo_manager.get_saldo_atual():
                            st.error(f"⚠️ Saldo insuficiente! Necessário: R$ {valor_operacao:,.2f}, Disponível: {saldo_manager.get_saldo_formatado()}")
                    
                    # BOTÃO PARA VISUALIZAR PDF (OBRIGATÓRIO)
                    st.markdown("---")
                    col_view1, col_view2 = st.columns([1, 1])
                    with col_view1:
                        if st.button("👁️ VISUALIZAR PDF", key=f"view_{pdf_id}", use_container_width=True):
                            st.session_state[f'current_viewing_pdf'] = pdf_id
                            st.rerun()
                    
                    # Se este PDF está sendo visualizado, mostrar o visualizador
                    if st.session_state.get('current_viewing_pdf') == pdf_id:
                        mostrar_visualizador_pdf(pdf_id, pdf_data)
                        
                        # Marcar como visualizado
                        st.session_state[f'pdf_viewed_{pdf_id}'] = True
                        st.success("✅ PDF visualizado. Agora você pode proceder com a homologação.")
                    
                    # BOTÕES DE HOMOLOGAÇÃO (só aparecem após visualização)
                    pdf_visualizado = st.session_state.get(f'pdf_viewed_{pdf_id}', False)

                    if pdf_visualizado:
                        st.markdown("### 🎯 AÇÃO DE HOMOLOGAÇÃO")
                        
                        # Extrair número do P Trab automaticamente do nome do arquivo
                        numero_ptrab_extraido = extrair_numero_ptrab_do_nome(pdf_data['nome_arquivo'])
                        
                        if numero_ptrab_extraido:
                            st.info(f"**Número do P Trab detectado automaticamente:** `{numero_ptrab_extraido}`")
                            
                            # Mostrar campo editável caso queira corrigir
                            numero_ptrab = st.text_input(
                                "**Número do P Trab:**", 
                                value=numero_ptrab_extraido,
                                key=f"ptrab_{pdf_id}",
                                help="Número extraído automaticamente do nome do arquivo. Edite se necessário."
                            )
                        else:
                            st.warning("⚠️ Não foi possível detectar automaticamente o número do P Trab.")
                            numero_ptrab = st.text_input(
                                "**Número do P Trab:**", 
                                key=f"ptrab_{pdf_id}",
                                placeholder="Ex: P Trab Nr 00001/2024",
                                help="Informe o número do P Trab (não foi possível detectar automaticamente)"
                            )
                        
                        col_btn1, col_btn2 = st.columns(2)
                        
                        with col_btn1:
                            # Usar form para agrupar os elementos de aprovação
                            with st.form(key=f"approve_form_{pdf_id}"):
                                if not numero_ptrab.strip():
                                    st.error("❌ Número do P Trab é obrigatório para aprovação!")
                                
                                justificativa_aprovacao = st.text_input(
                                    "Justificativa (opcional):", 
                                    key=f"just_approve_{pdf_id}", 
                                    placeholder="Documento aprovado conforme análise..."
                                )
                                
                                col_confirm1, col_confirm2 = st.columns(2)
                                with col_confirm1:
                                    confirmar_aprovacao = st.form_submit_button(
                                        "🎯 CONFIRMAR APROVAÇÃO", 
                                        use_container_width=True,
                                        type="primary"
                                    )
                                
                                if confirmar_aprovacao:
                                    if not numero_ptrab.strip():
                                        st.error("❌ Número do P Trab é obrigatório para aprovação!")
                                    else:
                                        # Verificar saldo para operações de PREPARO
                                        tipo_operacao = pdf_data.get('tipo_operacao', '1')  # Default para EMPREGO se não existir
                                        if tipo_operacao == '2' and SALDO_MANAGER_CARREGADO:
                                            if valor_operacao > saldo_manager.get_saldo_atual():
                                                st.error(f"❌ Saldo insuficiente! Necessário: R$ {valor_operacao:,.2f}, Disponível: {saldo_manager.get_saldo_formatado()}")
                                            else:
                                                # Atualizar o PDF com o número do P Trab antes da homologação
                                                homologacao_system.pdf_uploads[pdf_id]['numero_ptrab'] = numero_ptrab
                                                success, msg = homologacao_system.homologar_pdf(
                                                    pdf_id, 
                                                    st.session_state.user_info['nome'], 
                                                    'aprovado', 
                                                    justificativa_aprovacao
                                                )
                                                if success:
                                                    st.success(f"✅ {msg}")
                                                    if tipo_operacao == '2' and valor_operacao > 0:
                                                        st.info(f"💰 Valor de R$ {valor_operacao:,.2f} abatido do saldo de preparo.")
                                                    
                                                    # Limpar estado de visualização
                                                    if f'pdf_viewed_{pdf_id}' in st.session_state:
                                                        del st.session_state[f'pdf_viewed_{pdf_id}']
                                                    if 'current_viewing_pdf' in st.session_state:
                                                        del st.session_state['current_viewing_pdf']
                                                    
                                                    st.rerun()
                                                else:
                                                    st.error(f"❌ {msg}")
                                        else:
                                            # Para operações de EMPREGO ou quando não há saldo manager
                                            # Atualizar o PDF com o número do P Trab antes da homologação
                                            homologacao_system.pdf_uploads[pdf_id]['numero_ptrab'] = numero_ptrab
                                            success, msg = homologacao_system.homologar_pdf(
                                                pdf_id, 
                                                st.session_state.user_info['nome'], 
                                                'aprovado', 
                                                justificativa_aprovacao
                                            )
                                            if success:
                                                st.success(f"✅ {msg}")
                                                
                                                # Limpar estado de visualização
                                                if f'pdf_viewed_{pdf_id}' in st.session_state:
                                                    del st.session_state[f'pdf_viewed_{pdf_id}']
                                                if 'current_viewing_pdf' in st.session_state:
                                                    del st.session_state['current_viewing_pdf']
                                                
                                                st.rerun()
                                            else:
                                                st.error(f"❌ {msg}")
                        
                        with col_btn2:
                            # Usar form para agrupar os elementos de rejeição
                            with st.form(key=f"reject_form_{pdf_id}"):
                                justificativa_rejeicao = st.text_input(
                                    "Justificativa (OBRIGATÓRIA para rejeição):", 
                                    key=f"just_reject_{pdf_id}", 
                                    placeholder="Informe o motivo da rejeição..."
                                )
                                
                                col_confirm3, col_confirm4 = st.columns(2)
                                with col_confirm3:
                                    confirmar_rejeicao = st.form_submit_button(
                                        "🎯 CONFIRMAR REJEIÇÃO", 
                                        use_container_width=True,
                                        type="secondary"
                                    )
                                
                                if confirmar_rejeicao:
                                    if not justificativa_rejeicao.strip():
                                        st.error("❌ Justificativa obrigatória para rejeição!")
                                    else:
                                        # Atualizar o PDF com o número do P Trab antes da homologação
                                        homologacao_system.pdf_uploads[pdf_id]['numero_ptrab'] = numero_ptrab
                                        success, msg = homologacao_system.homologar_pdf(
                                            pdf_id, 
                                            st.session_state.user_info['nome'], 
                                            'rejeitado', 
                                            justificativa_rejeicao
                                        )
                                        if success:
                                            st.success(f"✅ {msg}")
                                            if tipo_operacao == '2' and valor_operacao > 0:
                                                st.info("🔄 Nenhum valor foi abatido do saldo (documento rejeitado).")
                                            
                                            # Limpar estado de visualização
                                            if f'pdf_viewed_{pdf_id}' in st.session_state:
                                                del st.session_state[f'pdf_viewed_{pdf_id}']
                                            if 'current_viewing_pdf' in st.session_state:
                                                del st.session_state['current_viewing_pdf']
                                            
                                            st.rerun()
                                        else:
                                            st.error(f"❌ {msg}")
                    else:
                        st.warning("⚠️ **Visualize o PDF acima antes de prosseguir com a homologação**")
                    
        else:
            st.info("📝 Nenhum documento pendente de homologação.")
    
    with tab2:
        st.subheader("✅ Documentos Aprovados")
        pdfs_aprovados = homologacao_system.get_pdfs_aprovados()
        
        if pdfs_aprovados:
            for pdf_id, pdf_data in pdfs_aprovados.items():
                with st.expander(f"📄 {pdf_data['nome_arquivo']} - {pdf_data['usuario']}", expanded=False):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**Aprovado em:** {pdf_data['data_homologacao'][:16]}")
                        st.write(f"**Por:** {pdf_data['homologador']}")
                        st.write(f"**Usuário:** {pdf_data['usuario']} ({pdf_data['posto_usuario']})")
                        st.write(f"**OM:** {pdf_data['om_usuario']}")
                        if pdf_data.get('numero_ptrab'):
                            st.write(f"**Nº P Trab:** {pdf_data['numero_ptrab']}")
                    with col2:
                        st.write(f"**Operação:** {pdf_data['dados_operacao'].get('nome_operacao', 'N/A')}")
                        tipo_operacao = pdf_data.get('tipo_operacao', '1')
                        st.write(f"**Tipo:** {'PREPARO' if tipo_operacao == '2' else 'EMPREGO'}")
                        valor_operacao = pdf_data.get('valor_operacao', 0)
                        if valor_operacao > 0:
                            valor_formatado = f"R$ {valor_operacao:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                            st.write(f"**Valor:** {valor_formatado}")
                        if pdf_data.get('justificativa'):
                            st.write(f"**Justificativa:** {pdf_data['justificativa']}")
                    
                    # Botão para visualizar PDF aprovado
                    if st.button("👁️ VISUALIZAR PDF", key=f"view_approved_{pdf_id}", use_container_width=True):
                        st.session_state[f'current_viewing_pdf'] = pdf_id
                        st.rerun()
                    
                    if st.session_state.get('current_viewing_pdf') == pdf_id:
                        mostrar_visualizador_pdf(pdf_id, pdf_data)
                    
                    # Botão para excluir (apenas master)
                    if user_perfil == 'master':
                        if st.button("🗑️ EXCLUIR", key=f"delete_approved_{pdf_id}", use_container_width=True):
                            if st.checkbox("Confirmar exclusão deste documento?", key=f"confirm_delete_{pdf_id}"):
                                success, msg = homologacao_system.excluir_pdf(pdf_id, st.session_state.user_info['nome'])
                                if success:
                                    st.success(msg)
                                    st.rerun()
                                else:
                                    st.error(msg)
        else:
            st.info("📝 Nenhum documento aprovado.")
    
    with tab3:
        st.subheader("❌ Documentos Rejeitados")
        pdfs_rejeitados = homologacao_system.get_pdfs_rejeitados()
        
        if pdfs_rejeitados:
            for pdf_id, pdf_data in pdfs_rejeitados.items():
                with st.expander(f"📄 {pdf_data['nome_arquivo']} - {pdf_data['usuario']}", expanded=False):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**Rejeitado em:** {pdf_data['data_homologacao'][:16]}")
                        st.write(f"**Por:** {pdf_data['homologador']}")
                        st.write(f"**Usuário:** {pdf_data['usuario']} ({pdf_data['posto_usuario']})")
                    with col2:
                        st.write(f"**Operação:** {pdf_data['dados_operacao'].get('nome_operacao', 'N/A')}")
                        st.write(f"**Justificativa:** {pdf_data.get('justificativa', 'N/A')}")
                        if pdf_data.get('numero_ptrab'):
                            st.write(f"**Nº P Trab:** {pdf_data['numero_ptrab']}")
                    
                    # Botão para visualizar PDF rejeitado
                    if st.button("👁️ VISUALIZAR PDF", key=f"view_rejected_{pdf_id}", use_container_width=True):
                        st.session_state[f'current_viewing_pdf'] = pdf_id
                        st.rerun()
                    
                    if st.session_state.get('current_viewing_pdf') == pdf_id:
                        mostrar_visualizador_pdf(pdf_id, pdf_data)
                    
                    # Botão para excluir (apenas master)
                    if user_perfil == 'master':
                        if st.button("🗑️ EXCLUIR", key=f"delete_rejected_{pdf_id}", use_container_width=True):
                            if st.checkbox("Confirmar exclusão deste documento?", key=f"confirm_delete_rej_{pdf_id}"):
                                success, msg = homologacao_system.excluir_pdf(pdf_id, st.session_state.user_info['nome'])
                                if success:
                                    st.success(msg)
                                    st.rerun()
                                else:
                                    st.error(msg)
        else:
            st.info("📝 Nenhum documento rejeitado.")
    
    with tab4:
        st.subheader("📊 Extrato de Transações")
        if SALDO_MANAGER_CARREGADO:
            extrato = saldo_manager.get_extrato(limite=100)
            
            if extrato:
                # Converter para DataFrame para melhor visualização
                extrato_data = []
                for transacao in reversed(extrato):
                    valor_formatado = f"R$ {transacao['valor']:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                    saldo_anterior_formatado = f"R$ {transacao['saldo_anterior']:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                    saldo_posterior_formatado = f"R$ {transacao['saldo_posterior']:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                    
                    extrato_data.append({
                        'Data': transacao['data'][:16],
                        'Tipo': transacao['tipo'].upper(),
                        'Valor': valor_formatado,
                        'Descrição': transacao['descricao'],
                        'Nº P Trab': transacao.get('numero_ptrab', 'N/A'),
                        'Homologador': transacao['homologador'],
                        'Saldo Anterior': saldo_anterior_formatado,
                        'Saldo Posterior': saldo_posterior_formatado
                    })
                
                df = pd.DataFrame(extrato_data)
                st.dataframe(df, use_container_width=True)
                
                # Estatísticas
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    total_abatimentos = sum(t['valor'] for t in extrato if t['tipo'] == 'abatimento')
                    total_abatimentos_formatado = f"R$ {total_abatimentos:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                    st.metric("Total Abatido", total_abatimentos_formatado)
                with col2:
                    total_estornos = sum(t['valor'] for t in extrato if t['tipo'] == 'estorno')
                    total_estornos_formatado = f"R$ {total_estornos:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                    st.metric("Total Estornado", total_estornos_formatado)
                with col3:
                    st.metric("Saldo Atual", saldo_manager.get_saldo_formatado())
                with col4:
                    transacoes_preparo = [t for t in extrato if 'PREPARO' in t.get('descricao', '') or t.get('numero_ptrab')]
                    st.metric("Transações P Trab", len(transacoes_preparo))
            else:
                st.info("📝 Nenhuma transação registrada.")
        else:
            st.error("❌ Gerenciador de saldo não carregado.")

def show_pdf_upload_tab():
    """Exibe a aba para carregar PDF assinado com valor da operação"""
    st.markdown('<div class="section-header">📄 CARREGAR PDF ASSINADO</div>', unsafe_allow_html=True)
    
    st.info("""
    📋 **Instruções:**
    - Faça o upload do PDF assinado digitalmente
    - Apenas arquivos PDF são aceitos
    - O documento será enviado para homologação COTER
    - Para operações de PREPARO, informe o valor para controle do saldo
    """)
    
    uploaded_file = st.file_uploader("**Selecione o PDF assinado:**", type=['pdf'])
    
    # Verificar tipo de operação para solicitar valor
    dados_operacao = st.session_state.dados_completos.get('operacao', {})
    tipo_operacao = dados_operacao.get('tipo', '1')
    
    valor_operacao = 0.0
    if tipo_operacao == '2':  # PREPARO
        valor_operacao = st.number_input(
            "**Valor da Operação de PREPARO (R$):**", 
            min_value=0.0, 
            value=0.0, 
            step=1000.0,
            help="Informe o valor total da operação de preparo para controle do saldo"
        )
    
    if uploaded_file is not None:
        if uploaded_file.type == "application/pdf":
            st.success("✅ Arquivo PDF válido!")
            
            if st.button("📤 ENVIAR PARA HOMOLOGAÇÃO", use_container_width=True):
                pdf_id = homologacao_system.register_pdf_upload(
                    uploaded_file, 
                    st.session_state.user_info, 
                    dados_operacao,
                    valor_operacao
                )
                uploads_dir = "pdf_uploads"
                os.makedirs(uploads_dir, exist_ok=True)
                file_path = os.path.join(uploads_dir, f"{pdf_id}_{uploaded_file.name}")
                with open(file_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                st.success(f"✅ PDF enviado para homologação com ID: {pdf_id}")
                if tipo_operacao == '2' and valor_operacao > 0:
                    valor_formatado = f"R$ {valor_operacao:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                    st.info(f"💰 Valor de {valor_formatado} registrado para controle de saldo.")
        else:
            st.error("❌ Erro: Apenas arquivos PDF são aceitos!")

def show_cabecalho_tab():
    st.markdown('<div class="section-header">DADOS DO CABEÇALHO</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        unidade = st.text_input("**Unidade:**", value="15ª BRIGADA DE INFANTARIA MECANIZADA")
    with col2:
        titulo_unidade = st.text_input("**Título da Unidade:**", value="BRIGADA GUARANI")
    
    st.session_state.dados_completos['cabecalho'] = {
        'unidade': unidade,
        'titulo_unidade': titulo_unidade
    }

def show_operacao_tab():
    st.markdown('<div class="section-header">INFORMAÇÕES DA OPERAÇÃO</div>', unsafe_allow_html=True)
    
    tipo_operacao = st.radio("**Tipo de Operação:**", ["EMPREGO", "PREPARO"], horizontal=True, index=0)
    
    col1, col2 = st.columns(2)
    with col1:
        nome_operacao = st.text_input("**Nome da Operação:**", "OP PUNHOS DE AÇO")
        periodo = st.text_input("**Período (DD/MM/AAAA A DD/MM/AAAA):**", "12/10/2026 A 25/11/2026")
        local = st.text_input("**Local:**", "Cascavel-PR")
        solicitante = st.text_input("**Solicitante:**", "Comando Militar do Sul")
    
    with col2:
        descricao = st.text_area("**Descrição:**", "Realizar Reconhecimento de Eixo")
        faseamento = st.text_input("**Faseamento:**", "PAA")
        composicao_meios = st.text_input("**Composição dos meios:**", "OM da 15ª Bda Inf Mec")
        efetivo_total = st.text_input("**Efetivo total:**", "2200")
    
    st.session_state.dados_completos['operacao'] = {
        'nome_operacao': nome_operacao,
        'periodo': periodo,
        'local': local,
        'solicitante': solicitante,
        'descricao': descricao,
        'faseamento': faseamento,
        'composicao_meios': composicao_meios,
        'efetivo_total': efetivo_total,
        'tipo': '1' if tipo_operacao == 'EMPREGO' else '2'
    }

def show_alimentacao_tab():
    st.markdown('<div class="section-header">ITENS DE ALIMENTAÇÃO</div>', unsafe_allow_html=True)
    
    with st.expander("➕ ADICIONAR NOVO ITEM", expanded=True):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Tipos de itens disponíveis
            tipos_itens = ["QR", "QS", "Ração Operacional"]
            tipo_item = st.selectbox("**Tipo:**", tipos_itens)
            
            # Se for Ração Operacional, mostrar seleção do tipo de ração
            if tipo_item == "Ração Operacional":
                tipo_racao = st.selectbox("**Tipo de Ração:**", ["R2", "R3", "RA"])
                tipo_item_completo = f"Rção Operacional ({tipo_racao})"
            else:
                tipo_racao = ""
                tipo_item_completo = tipo_item
            
            efetivo = st.number_input("**Efetivo:**", min_value=1, value=100, step=1)
            dias = st.number_input("**Dias:**", min_value=1, value=45, step=1)
        
        with col2:
            # Campo de pesquisa CODOM
            st.write("**Pesquisar CODOM:**")
            codom_pesquisa = st.text_input(
                "Digite código ou nome da OM:",
                key="codom_pesquisa_input_auth",
                label_visibility="collapsed",
                placeholder="Pesquise por código CODOM ou nome da OM..."
            )
            
            # Atualizar session_state quando o campo de pesquisa mudar
            if codom_pesquisa != st.session_state.get('codom_pesquisa_anterior_auth', ''):
                st.session_state.codom_pesquisa_auth = codom_pesquisa
                st.session_state.codom_pesquisa_anterior_auth = codom_pesquisa
            
            # Lista de CODOMs filtrados
            if CODOM_MANAGER_CARREGADO:
                if st.session_state.get('codom_pesquisa_auth', ''):
                    opcoes_codom = codom_manager.search_options(st.session_state.codom_pesquisa_auth)
                else:
                    opcoes_codom = codom_manager.get_all_options()
            else:
                opcoes_codom = ["CODOM não disponível"]
            
            # Selectbox com todas as opções
            codom_selecionado = st.selectbox(
                "**Selecione o CODOM:**",
                options=opcoes_codom,
                index=0,
                key="codom_selectbox_auth"
            )
            
            # Vinculação automática
            vinculacao_ativa = st.checkbox(
                "Vincular CODOM ao CODUG automaticamente",
                value=True,
                help="Quando marcado, o CODUG será preenchido automaticamente baseado no CODOM selecionado"
            )
        
        with col3:
            # Campos que serão preenchidos automaticamente
            om_auto, codug_auto = atualizar_dados_automaticos_auth(
                tipo_item, 
                codom_selecionado, 
                vinculacao_ativa
            )
            
            # Campo OM agora é somente leitura quando vinculação está ativa
            om = st.text_input(
                "**OM (Organização Militar):**", 
                value=om_auto,
                disabled=vinculacao_ativa,
                help="Preenchido automaticamente quando a vinculação está ativa"
            )
            
            codug = st.text_input(
                "**CODUG (6 dígitos):**", 
                value=codug_auto, 
                disabled=vinculacao_ativa,
                help="Automaticamente preenchido quando a vinculação está ativa"
            )
            
            # Mostrar refeições intermediárias apenas para QR/QS em operações de EMPREGO
            tipo_operacao_atual = st.session_state.dados_completos.get('operacao', {}).get('tipo', '1')
            
            if tipo_item in ['QR', 'QS'] and tipo_operacao_atual == '1':  # EMPREGO
                refeicoes = st.number_input("**Refeições Intermediárias (1-3):**", 
                                          min_value=1, max_value=3, value=2, step=1)
                st.info("💡 Campo disponível apenas para QR/QS em operações de EMPREGO")
            else:
                refeicoes = 0
                if tipo_item in ['QR', 'QS']:
                    st.write("**Refeições Intermediárias:**")
                    st.warning("⚠️ Não disponível para operações de PREPARO")
                else:
                    # Para Ração Operacional, mostrar informações específicas
                    if tipo_item == "Ração Operacional":
                        st.markdown('<div class="racao-box">', unsafe_allow_html=True)
                        st.write("**Ração Operacional**")
                        quantidade_racoes = efetivo * dias
                        st.write(f"Quantidade calculada: **{quantidade_racoes} {tipo_racao}**")
                        st.markdown('</div>', unsafe_allow_html=True)
        
        # DEBUG - Verificar Vinculação CODOM-CODUG
        with st.expander("🔍 DEBUG - Verificar Vinculação CODOM-CODUG"):
            if codom_selecionado and CODOM_MANAGER_CARREGADO and codom_selecionado != "Selecione o CODOM":
                codom_limpo = codom_manager.extract_codom_from_selection(codom_selecionado)
                if codom_limpo in codom_manager.codom_data:
                    dados = codom_manager.codom_data[codom_limpo]
                    st.write(f"**CODOM:** {codom_limpo}")
                    st.write(f"**Descrição:** {dados['descricao']}")
                    st.write(f"**SIGLA QR:** {dados['sigla_qr']} | **CODUG QR:** {dados['codug_qr']}")
                    st.write(f"**SIGLA QS:** {dados['sigla_qs']} | **CODUG QS:** {dados['codug_qs']}")
                    
                    # Mostrar o que será usado para o tipo selecionado
                    sigla_correta = codom_manager.get_sigla_for_tipo(codom_selecionado, tipo_item)
                    codug_correta = codom_manager.get_codug_for_tipo(codom_selecionado, tipo_item)
                    st.write(f"**Para {tipo_item}:**")
                    st.write(f"  - SIGLA que aparecerá no PDF: **'{sigla_correta}'**")
                    st.write(f"  - CODUG que aparecerá no PDF: **'{codug_correta}'**")
                    st.write(f"  - Coluna 'OM (UGE) CODUG' no PDF: **'{sigla_correta} ({codug_correta})'**")
                else:
                    st.warning("CODOM não encontrado na base de dados")
            else:
                st.info("Selecione um CODOM válido para ver as informações")
        
        # Botão para adicionar item
        col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
        with col_btn2:
            if st.button("✅ ADICIONAR ITEM", type="primary", use_container_width=True, key="add_item_auth"):
                # Validações
                errors = []
                
                # Validar CODOM
                if not codom_selecionado or codom_selecionado == "Selecione o CODOM":
                    errors.append("Selecione um CODOM válido")
                else:
                    # Extrair código CODOM da seleção
                    codom_limpo = codom_manager.extract_codom_from_selection(codom_selecionado)
                    if codom_limpo not in codom_manager.codom_data:
                        errors.append("CODOM selecionado não encontrado na base de dados")
                
                # Validar CODUG
                if not codug.strip():
                    errors.append("CODUG deve ser preenchido")
                elif len(codug) != 6:
                    errors.append("CODUG deve ter exatamente 6 dígitos")
                elif not codug.startswith('160'):
                    errors.append("CODUG deve começar com 160")
                
                # Validar OM
                if not om.strip():
                    errors.append("OM deve ser preenchida")
                
                # Validar dados numéricos
                if efetivo <= 0:
                    errors.append("Efetivo deve ser maior que 0")
                if dias <= 0:
                    errors.append("Dias deve ser maior que 0")
                
                # Validações específicas para refeições intermediárias
                if tipo_item in ['QR', 'QS'] and tipo_operacao_atual == '1':
                    if refeicoes < 1 or refeicoes > 3:
                        errors.append("Refeições intermediárias devem estar entre 1-3 para QR/QS em operações de EMPREGO")
                
                # Validar vinculação CODOM-CODUG
                if vinculacao_ativa and CODOM_MANAGER_CARREGADO:
                    # Verificar se o CODUG gerado corresponde ao esperado para o tipo
                    codug_esperado = codom_manager.get_codug_for_tipo(codom_selecionado, tipo_item)
                    if codug != codug_esperado:
                        st.warning(f"⚠️ CODUG não corresponde ao esperado para {tipo_item}. Esperado: {codug_esperado}")
                
                if errors:
                    for error in errors:
                        st.error(error)
                else:
                    # Preparar dados do item
                    novo_item = {
                        'tipo': tipo_item,
                        'tipo_completo': tipo_item_completo,
                        'efetivo': efetivo,
                        'dias': dias,
                        'om': om,
                        'codug': codug,
                        'codom': codom_limpo,
                        'refeicoes_intermediarias': refeicoes,
                        'vinculacao_automatica': vinculacao_ativa,
                        'eh_racao_operacional': tipo_item == "Ração Operacional"
                    }
                    
                    # Adicionar informações específicas para ração operacional
                    if tipo_item == "Ração Operacional":
                        novo_item['tipo_racao'] = tipo_racao
                        quantidade_racoes, valor_unitario, valor_total = calcular_racao_operacional(efetivo, dias, tipo_racao)
                        novo_item['quantidade_racoes'] = quantidade_racoes
                        novo_item['valor_unitario'] = valor_unitario
                        novo_item['valor_total'] = valor_total
                        
                        # Gerar descrição e cálculo
                        nome_op = st.session_state.dados_completos.get('operacao', {}).get('nome_operacao', '')
                        novo_item['descricao_racao'] = gerar_descricao_racao_operacional(efetivo, dias, tipo_racao, nome_op)
                        calculo, quantidade = gerar_calculo_racao_operacional(efetivo, dias, tipo_racao)
                        novo_item['calculo_racao'] = calculo
                    
                    st.session_state.itens_alimentacao.append(novo_item)
                    st.success(f"✅ Item {tipo_item_completo} adicionado com sucesso!")
                    st.rerun()

    # Lista de itens adicionados
    st.markdown("### 📋 Itens Adicionados")
    if st.session_state.itens_alimentacao:
        for i, item in enumerate(st.session_state.itens_alimentacao):
            with st.container():
                col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
                with col1:
                    if item['eh_racao_operacional']:
                        st.write(f"**Item {i+1}:** 🎯 Ração Operacional {item.get('tipo_racao', '')}")
                        st.write(f"**Quantidade:** {item.get('quantidade_racoes', 0)} rações")
                    else:
                        st.write(f"**Item {i+1}:** {item['tipo']} - {item['efetivo']} militares")
                        if item['refeicoes_intermediarias'] > 0:
                            st.write(f"**Refeições:** {item['refeicoes_intermediarias']}")
                    st.write(f"**OM:** {item['om']}")
                with col2:
                    st.write(f"**Dias:** {item['dias']}")
                    st.write(f"**CODOM:** {item['codom']}")
                with col3:
                    st.write(f"**CODUG:** {item['codug']}")
                    if item['vinculacao_automatica']:
                        st.write("🔗 **Vinculação automática**")
                    if item['eh_racao_operacional']:
                        st.write("💰 **Valor:** R$ 0,00")
                with col4:
                    if st.button("🗑️", key=f"remover_auth_{i}"):
                        st.session_state.itens_alimentacao.pop(i)
                        st.rerun()
                st.markdown("---")
        
        # Estatísticas dos itens
        col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)
        with col_stat1:
            st.metric("Total de Itens", len(st.session_state.itens_alimentacao))
        with col_stat2:
            tipos_qr = len([item for item in st.session_state.itens_alimentacao if item['tipo'] == 'QR'])
            st.metric("Itens QR", tipos_qr)
        with col_stat3:
            tipos_qs = len([item for item in st.session_state.itens_alimentacao if item['tipo'] == 'QS'])
            st.metric("Itens QS", tipos_qs)
        with col_stat4:
            tipos_racao = len([item for item in st.session_state.itens_alimentacao if item['eh_racao_operacional']])
            st.metric("Rações Operacionais", tipos_racao)
            
    else:
        st.info("📝 Nenhum item de alimentação adicionado ainda.")

def show_assinatura_tab():
    st.markdown('<div class="section-header">ASSINATURA DO DOCUMENTO</div>', unsafe_allow_html=True)
    
    st.info("""
    ✍️ **Assinatura do Plano de Trabalho**
    
    Preencha os dados para assinatura do documento.
    """)
    
    with st.form("assinatura_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            local_emissao = st.text_input("Local de Emissão:", value="Cascavel-PR")
            nome_militar = st.text_input("Nome do Militar:", value=st.session_state.user_info['nome'])
            posto = st.text_input("Posto/Graduação:", value=st.session_state.user_info['posto'])
        
        with col2:
            funcao = st.text_input("Função:", value="Chefe do Estado-Maior da 15ª Brigada de Infantaria Mecanizada")
            om_assinatura = st.text_input("OM:", value=st.session_state.user_info['om'])
        
        if st.form_submit_button("💾 SALVAR DADOS DE ASSINATURA"):
            st.session_state.dados_assinatura = {
                'local': local_emissao,
                'militar': f"{nome_militar.upper()} - {posto}",
                'funcao': funcao,
                'om': om_assinatura
            }
            st.success("✅ Dados de assinatura salvos!")
    
    # Mostrar dados salvos
    if 'dados_assinatura' in st.session_state:
        st.subheader("Dados de Assinatura Salvos")
        st.json(st.session_state.dados_assinatura)

def show_gerar_pdf_tab():
    st.markdown('<div class="section-header">GERAR PDF DO PLANO DE TRABALHO</div>', unsafe_allow_html=True)
    
    # Resumo dos dados
    st.markdown("### 📊 RESUMO DOS DADOS")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Itens de Alimentação", len(st.session_state.itens_alimentacao))
    with col2:
        if st.session_state.dados_completos.get('operacao'):
            st.metric("Operação", st.session_state.dados_completos['operacao']['nome_operacao'])
    with col3:
        if st.session_state.dados_completos.get('cabecalho'):
            st.metric("Unidade", st.session_state.dados_completos['cabecalho']['unidade'][:20] + "...")
    with col4:
        tipo_op = st.session_state.dados_completos.get('operacao', {}).get('tipo', '1')
        st.metric("Tipo", "EMPREGO" if tipo_op == '1' else "PREPARO")
    
    # Botão de geração
    st.markdown("### 🚀 GERAR DOCUMENTO")
    
    if not st.session_state.itens_alimentacao:
        st.warning("⚠️ Adicione pelo menos um item de alimentação antes de gerar o PDF.")
    else:
        col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
        with col_btn2:
            if st.button("📄 GERAR PDF DO PLANO DE TRABALHO", type="primary", use_container_width=True):
                with st.spinner("🔄 Gerando PDF... Aguarde..."):
                    try:
                        # Coletar dados completos
                        dados_cabecalho = st.session_state.dados_completos['cabecalho']
                        dados_operacao = st.session_state.dados_completos['operacao']
                        dados_assinatura = st.session_state.dados_assinatura
                        
                        # Gerar número de controle
                        gerador = GeradorPDFPTrab()
                        numero_controle = gerador.obter_numero_controle()
                        
                        # Nome do arquivo
                        nome_unidade = dados_cabecalho['unidade']
                        nome_unidade_limpo = re.sub(r'[^\w\s]', '', nome_unidade)
                        nome_unidade_arquivo = nome_unidade_limpo.replace(" ", "_").upper()
                        numero_ptrab = numero_controle.replace("P Trab Nr ", "").replace("/", "_")
                        nome_arquivo = f"P_TRAB_{nome_unidade_arquivo}_{numero_ptrab}.pdf"
                        
                        # Usar a mesma função de criação de PDF
                        sucesso = criar_pdf_real(
                            dados_cabecalho, 
                            dados_operacao, 
                            st.session_state.itens_alimentacao,
                            dados_assinatura, 
                            nome_arquivo, 
                            numero_controle
                        )
                        
                        if sucesso:
                            st.success(f"✅ PDF gerado com sucesso: {nome_arquivo}")
                            
                            # Mostrar resumo
                            st.markdown("### 📋 RESUMO DA GERAÇÃO")
                            
                            # Calcular totais
                            total_geral = 0
                            total_racoes = 0
                            for item in st.session_state.itens_alimentacao:
                                if item['eh_racao_operacional']:
                                    total_racoes += item.get('quantidade_racoes', 0)
                                else:
                                    # Calcular valor para QR/QS
                                    if MODULO_OPERACIONAL_CARREGADO:
                                        if dados_operacao['tipo'] == '1':  # EMPREGO
                                            valor_total, _ = gerador.calcular_valores_emprego(
                                                item['efetivo'], 
                                                item['dias'],
                                                item['refeicoes_intermediarias'], 
                                                item['tipo']
                                            )
                                        else:  # PREPARO
                                            valor_total, _ = gerador.calcular_valores_preparo(
                                                item['efetivo'], 
                                                item['dias'],
                                                item['tipo']
                                            )
                                        total_geral += valor_total
                            
                            col1, col2, col3, col4 = st.columns(4)
                            with col1:
                                st.metric("Total de itens", len(st.session_state.itens_alimentacao))
                            with col2:
                                st.metric("Número de controle", numero_controle)
                            with col3:
                                total_geral_formatado = f"R$ {total_geral:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                                st.metric("Valor total", total_geral_formatado)
                            with col4:
                                if total_racoes > 0:
                                    st.metric("Rações operacionais", f"{total_racoes} un")
                            
                            # Botão de download
                            if os.path.exists(nome_arquivo):
                                with open(nome_arquivo, "rb") as file:
                                    st.download_button(
                                        label="📥 BAIXAR PDF",
                                        data=file,
                                        file_name=nome_arquivo,
                                        mime="application/pdf",
                                        use_container_width=True
                                    )
                            else:
                                st.warning("⚠️ Arquivo PDF não foi encontrado para download.")
                        else:
                            st.error("❌ Falha ao gerar o PDF. Verifique os dados e tente novamente.")
                        
                    except Exception as e:
                        st.error(f"❌ Erro ao gerar PDF: {str(e)}")
                        import traceback
                        st.code(traceback.format_exc())

# VERIFICAÇÃO SIMPLIFICADA DO USUÁRIO MASTER
def verificar_e_criar_usuario_master():
    """Verifica e cria o usuário master se necessário"""
    try:
        auth_system.load_users()
        master_cpf = "00000000000"
        
        if master_cpf not in auth_system.users:
            print("🔧 Criando usuário master...")
            success, message = auth_system.register_user(
                nome="ADMINISTRADOR MASTER",
                posto="CEL", 
                om="6122 - 40º BI",
                cpf=master_cpf,
                email="admin@system.com",
                password="Master123!",
                perfil="master",
                cadastrado_por="SISTEMA"
            )
            if success:
                print("✅ Usuário master criado com sucesso!")
            else:
                print(f"❌ Erro ao criar usuário master: {message}")
        else:
            print("✅ Usuário master já existe")
            
    except Exception as e:
        print(f"❌ Erro na verificação do usuário master: {e}")

# DEBUG - Testar login do master
def testar_login_master():
    auth_system.load_users()
    master_cpf = "00000000000"
    
    if master_cpf in auth_system.users:
        print("🔍 DEBUG - Usuário master encontrado!")
        success, result = auth_system.login(master_cpf, "Master123!")
        print(f"🔍 DEBUG - Login testado: {success}, {result}")
    else:
        print("🔍 DEBUG - Usuário master NÃO encontrado!")

# Executar verificação
verificar_e_criar_usuario_master()
testar_login_master()

# Função principal
def main():
    add_bg_image()
    
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    
    if 'show_forgot_password' not in st.session_state:
        st.session_state.show_forgot_password = False
    
    if 'dados_completos' not in st.session_state:
        st.session_state.dados_completos = {}
    if 'itens_alimentacao' not in st.session_state:
        st.session_state.itens_alimentacao = []
    if 'dados_assinatura' not in st.session_state:
        st.session_state.dados_assinatura = {}
    
    # INICIALIZAR VARIÁVEIS DE CODOM PARA A VERSÃO COM AUTH
    if 'codom_pesquisa_auth' not in st.session_state:
        st.session_state.codom_pesquisa_auth = ""
    if 'codom_pesquisa_anterior_auth' not in st.session_state:
        st.session_state.codom_pesquisa_anterior_auth = ""
    
    if not st.session_state.logged_in:
        show_login_page()
        return
    
    user_perfil = st.session_state.user_info['perfil']
    user_nome = st.session_state.user_info['nome']
    
    st.markdown('<div class="main-container">', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([3, 2, 1])
    with col1:
        try:
            if os.path.exists('colog.png'):
                with open('colog.png', "rb") as image_file:
                    encoded_string = base64.b64encode(image_file.read()).decode()
                st.markdown(
                    f'''
                    <div style="text-align: center; margin-bottom: 1rem;">
                        <img src="data:image/png;base64,{encoded_string}" style="width: 80px; height: 80px; display: block; margin: 0 auto;">
                        <h1 style="color: #000000; font-weight: bold; margin: 10px 0 0 0;">SISTEMA DE PLANO DE TRABALHO LOGÍSTICO</h1>
                    </div>
                    ''', 
                    unsafe_allow_html=True
                )
            else:
                st.markdown(
                    '''
                    <div style="text-align: center; margin-bottom: 1rem;">
                        <div style="font-size: 3rem; margin-bottom: 10px;">⚙️</div>
                        <h1 style="color: #000000; font-weight: bold; margin: 0;">SISTEMA DE PLANO DE TRABALHO LOGÍSTICO</h1>
                    </div>
                    ''', 
                    unsafe_allow_html=True
                )
        except Exception as e:
            st.title("SISTEMA DE PLANO DE TRABALHO LOGÍSTICO")
    
    with col3:
        st.write(f"**Usuário:** {user_nome}")
        st.write(f"**Perfil:** {user_perfil.upper()}")
        if st.button("🚪 SAIR"):
            st.session_state.logged_in = False
            st.rerun()
    
    st.markdown("---")
    
    if not MODULO_OPERACIONAL_CARREGADO:
        st.error("❌ Módulo operacional não carregado!")
        st.markdown('</div>', unsafe_allow_html=True)
        return
        
    if not CODOM_MANAGER_CARREGADO:
        st.warning("⚠️ Gerenciador CODOM não carregado.")
    
    # CORREÇÃO: Definição correta das abas por perfil
    # ADICIONAR ABA "ALTERAR SENHA" PARA TODOS OS USUÁRIOS
    if user_perfil == 'usuário':
        tabs = ["📋 CABEÇALHO", "⚙️ OPERAÇÃO", "🍽️ ALIMENTAÇÃO", "✍️ ASSINATURA", "📄 GERAR PDF", "📄 CARREGAR PDF ASSINADO", "🔐 ALTERAR SENHA"]
    elif user_perfil == 'cadastrador':
        tabs = ["📋 CABEÇALHO", "⚙️ OPERAÇÃO", "🍽️ ALIMENTAÇÃO", "✍️ ASSINATURA", "📄 GERAR PDF", "📄 CARREGAR PDF ASSINADO", "👥 CADASTRO USUÁRIOS", "🔐 ALTERAR SENHA"]
    elif user_perfil == 'homologador':
        tabs = ["📄 HOMOLOGAÇÃO COTER", "🔐 ALTERAR SENHA"]
    else:  # master
        tabs = ["📋 CABEÇALHO", "⚙️ OPERAÇÃO", "🍽️ ALIMENTAÇÃO", "✍️ ASSINATURA", "📄 GERAR PDF", 
                "📄 CARREGAR PDF ASSINADO", "📄 HOMOLOGAÇÃO COTER", "👥 GESTÃO USUÁRIOS", "🔐 ALTERAR SENHA"]
    
    created_tabs = st.tabs(tabs)
    
    tab_functions = {
        "📋 CABEÇALHO": show_cabecalho_tab,
        "⚙️ OPERAÇÃO": show_operacao_tab,
        "🍽️ ALIMENTAÇÃO": show_alimentacao_tab,
        "✍️ ASSINATURA": show_assinatura_tab,
        "📄 GERAR PDF": show_gerar_pdf_tab,
        "📄 CARREGAR PDF ASSINADO": show_pdf_upload_tab,
        "📄 HOMOLOGAÇÃO COTER": show_homologacao_tab,
        "👥 CADASTRO USUÁRIOS": show_user_registration,
        "👥 GESTÃO USUÁRIOS": show_users_management,
        "🔐 ALTERAR SENHA": show_change_password
    }
    
    for tab_name, tab_obj in zip(tabs, created_tabs):
        with tab_obj:
            if tab_name in tab_functions:
                tab_functions[tab_name]()
    
    st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()