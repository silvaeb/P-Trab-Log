import streamlit as st
import pandas as pd
import hashlib
import secrets
import re
import smtplib
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart
import json
import os
from datetime import datetime, timedelta

class AuthenticationSystem:
    def __init__(self):
        self.users_file = 'users.json'
        self.tokens_file = 'password_tokens.json'
        self.load_users()
        self.load_tokens()
    
    def load_users(self):
        """Carrega os usuários do arquivo JSON"""
        try:
            if os.path.exists(self.users_file):
                with open(self.users_file, 'r', encoding='utf-8') as f:
                    self.users = json.load(f)
            else:
                self.users = {}
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
    
    def load_tokens(self):
        """Carrega os tokens de recuperação de senha"""
        try:
            if os.path.exists(self.tokens_file):
                with open(self.tokens_file, 'r') as f:
                    self.tokens = json.load(f)
            else:
                self.tokens = {}
                self.save_tokens()
        except Exception as e:
            st.error(f"Erro ao carregar tokens: {e}")
            self.tokens = {}
    
    def save_tokens(self):
        """Salva os tokens no arquivo JSON"""
        try:
            with open(self.tokens_file, 'w') as f:
                json.dump(self.tokens, f, indent=2)
        except Exception as e:
            st.error(f"Erro ao salvar tokens: {e}")
    
    def hash_password(self, password):
        """Faz o hash da senha usando SHA-256"""
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
    
    def register_user(self, nome, posto, om, cpf, email, password, perfil="usuário", cadastrado_por="master"):
        """Registra um novo usuário - GARANTE 1 CADASTRO POR CPF"""
        # Valida CPF (apenas numérico, 11 dígitos)
        cpf_clean = re.sub(r'\D', '', cpf)
        if len(cpf_clean) != 11:
            return False, "CPF deve conter 11 dígitos"
        
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
            'posto': posto.upper(),
            'om': om.upper(),
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
        """Realiza o login do usuário"""
        cpf_clean = re.sub(r'\D', '', cpf)
        
        if cpf_clean not in self.users:
            return False, "CPF não encontrado"
        
        user = self.users[cpf_clean]
        
        if not user['ativo']:
            return False, "Usuário inativo"
        
        if user['password'] != self.hash_password(password):
            return False, "Senha incorreta"
        
        return True, user
    
    def generate_reset_token(self, cpf):
        """Gera token para recuperação de senha"""
        cpf_clean = re.sub(r'\D', '', cpf)
        
        if cpf_clean not in self.users:
            return None
        
        token = secrets.token_urlsafe(32)
        expires = datetime.now() + timedelta(hours=24)
        
        self.tokens[token] = {
            'cpf': cpf_clean,
            'expires': expires.isoformat()
        }
        
        self.save_tokens()
        return token
    
    def validate_token(self, token):
        """Valida se o token é válido"""
        if token not in self.tokens:
            return False
        
        token_data = self.tokens[token]
        expires = datetime.fromisoformat(token_data['expires'])
        
        if datetime.now() > expires:
            del self.tokens[token]
            self.save_tokens()
            return False
        
        return token_data['cpf']
    
    def reset_password(self, token, new_password):
        """Redefine a senha do usuário"""
        cpf = self.validate_token(token)
        if not cpf:
            return False, "Token inválido ou expirado"
        
        is_valid, msg = self.validate_password(new_password)
        if not is_valid:
            return False, msg
        
        self.users[cpf]['password'] = self.hash_password(new_password)
        del self.tokens[token]
        
        self.save_users()
        self.save_tokens()
        
        return True, "Senha redefinida com sucesso"
    
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
        """Envia email com nova senha temporária"""
        cpf_clean = re.sub(r'\D', '', cpf)
        
        if cpf_clean not in self.users:
            return False, "Usuário não encontrado"
        
        user = self.users[cpf_clean]
        email = user['email']
        
        try:
            # Configurações do servidor SMTP (exemplo usando Gmail)
            # EM PRODUÇÃO: Configure estas variáveis de ambiente
            smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
            smtp_port = int(os.getenv('SMTP_PORT', 587))
            smtp_username = os.getenv('SMTP_USERNAME', '')
            smtp_password = os.getenv('SMTP_PASSWORD', '')
            
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
            
            # Enviar email
            if smtp_username and smtp_password:
                server = smtplib.SMTP(smtp_server, smtp_port)
                server.starttls()
                server.login(smtp_username, smtp_password)
                server.send_message(msg)
                server.quit()
                
                return True, "Email enviado com sucesso"
            else:
                # Modo desenvolvimento: mostrar a senha na interface
                return True, f"Modo desenvolvimento - Nova senha: {temp_password}"
                
        except Exception as e:
            # Em caso de erro no envio, ainda retorna a senha para o usuário
            return True, f"Erro no envio do email, mas sua nova senha é: {temp_password}"

# Instância global do sistema de autenticação
auth_system = AuthenticationSystem()