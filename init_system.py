import json
import os
from auth_system import auth_system

def initialize_system():
    """Inicializa o sistema com usuário master padrão se não existir"""
    
    # Verificar se já existe algum usuário
    if not auth_system.users:
        print("🔧 Inicializando sistema...")
        
        # Criar usuário master padrão
        success, message = auth_system.register_user(
            nome="ADMINISTRADOR MASTER",
            posto="MASTER",
            om="SISTEMA",
            cpf="00000000000",
            email="admin@system.com",
            password="Master123!",
            perfil="master",
            cadastrado_por="SISTEMA"
        )
        
        if success:
            print("✅ Usuário master criado com sucesso!")
            print("📋 Credenciais padrão:")
            print("   CPF: 00000000000")
            print("   Senha: Master123!")
            print("⚠️ Altere estas credenciais após o primeiro login!")
        else:
            print(f"❌ Erro ao criar usuário master: {message}")
    else:
        print("✅ Sistema já inicializado")

if __name__ == "__main__":
    initialize_system()