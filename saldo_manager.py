import json
import os
from datetime import datetime

class SaldoManager:
    def __init__(self):
        self.saldo_file = 'saldo_preparo.json'
        self.saldo_inicial = 5000000.00  # R$ 5.000.000,00
        self.load_saldo()
    
    def load_saldo(self):
        """Carrega o saldo do arquivo JSON"""
        try:
            if os.path.exists(self.saldo_file):
                with open(self.saldo_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.saldo_atual = data.get('saldo_atual', self.saldo_inicial)
                    self.transacoes = data.get('transacoes', [])
            else:
                self.saldo_atual = self.saldo_inicial
                self.transacoes = []
                self.save_saldo()
        except Exception as e:
            print(f"Erro ao carregar saldo: {e}")
            self.saldo_atual = self.saldo_inicial
            self.transacoes = []
    
    def save_saldo(self):
        """Salva o saldo no arquivo JSON"""
        try:
            data = {
                'saldo_inicial': self.saldo_inicial,
                'saldo_atual': self.saldo_atual,
                'transacoes': self.transacoes,
                'ultima_atualizacao': datetime.now().isoformat()
            }
            with open(self.saldo_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Erro ao salvar saldo: {e}")
    
    def get_saldo_atual(self):
        """Retorna o saldo atual formatado"""
        return self.saldo_atual
    
    def get_saldo_formatado(self):
        """Retorna o saldo formatado em moeda brasileira"""
        return f"R$ {self.saldo_atual:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    
    def abater_valor(self, pdf_id, valor, descricao, homologador):
        """Abate um valor do saldo (para PDFs aprovados)"""
        if valor <= 0:
            return False, "Valor deve ser maior que zero"
        
        if self.saldo_atual < valor:
            return False, f"Saldo insuficiente. Saldo atual: {self.get_saldo_formatado()}"
        
        self.saldo_atual -= valor
        
        transacao = {
            'id': pdf_id,
            'tipo': 'abatimento',
            'valor': valor,
            'descricao': descricao,
            'homologador': homologador,
            'data': datetime.now().isoformat(),
            'saldo_anterior': self.saldo_atual + valor,
            'saldo_posterior': self.saldo_atual
        }
        
        self.transacoes.append(transacao)
        self.save_saldo()
        
        return True, f"Valor de R$ {valor:,.2f} abatido com sucesso. Novo saldo: {self.get_saldo_formatado()}"
    
    def abater_valor_por_ptrab(self, numero_ptrab, valor, descricao, homologador):
        """Abate um valor do saldo usando número do P Trab como identificador"""
        if valor <= 0:
            return False, "Valor deve ser maior que zero"
        
        # Verificar se já existe transação para este P Trab
        for transacao in self.transacoes:
            if transacao.get('numero_ptrab') == numero_ptrab and transacao['tipo'] == 'abatimento':
                return False, f"Já existe um abatimento para o P Trab {numero_ptrab}"
        
        if self.saldo_atual < valor:
            return False, f"Saldo insuficiente. Saldo atual: {self.get_saldo_formatado()}"
        
        self.saldo_atual -= valor
        
        transacao = {
            'id': f"PTRAB_{numero_ptrab}",
            'numero_ptrab': numero_ptrab,
            'tipo': 'abatimento',
            'valor': valor,
            'descricao': descricao,
            'homologador': homologador,
            'data': datetime.now().isoformat(),
            'saldo_anterior': self.saldo_atual + valor,
            'saldo_posterior': self.saldo_atual
        }
        
        self.transacoes.append(transacao)
        self.save_saldo()
        
        return True, f"Valor de R$ {valor:,.2f} abatido com sucesso para {numero_ptrab}. Novo saldo: {self.get_saldo_formatado()}"
    
    def estornar_valor(self, pdf_id, homologador):
        """Estorna um valor previamente abatido (para PDFs excluídos/rejeitados)"""
        # Encontrar a transação pelo ID do PDF
        transacao_encontrada = None
        for transacao in self.transacoes:
            if transacao['id'] == pdf_id and transacao['tipo'] == 'abatimento':
                transacao_encontrada = transacao
                break
        
        if not transacao_encontrada:
            return False, "Transação não encontrada para estorno"
        
        valor_estorno = transacao_encontrada['valor']
        self.saldo_atual += valor_estorno
        
        transacao_estorno = {
            'id': pdf_id,
            'tipo': 'estorno',
            'valor': valor_estorno,
            'descricao': f"Estorno: {transacao_encontrada['descricao']}",
            'homologador': homologador,
            'data': datetime.now().isoformat(),
            'saldo_anterior': self.saldo_atual - valor_estorno,
            'saldo_posterior': self.saldo_atual
        }
        
        self.transacoes.append(transacao_estorno)
        self.save_saldo()
        
        return True, f"Valor de R$ {valor_estorno:,.2f} estornado com sucesso. Novo saldo: {self.get_saldo_formatado()}"
    
    def estornar_valor_por_ptrab(self, numero_ptrab, homologador):
        """Estorna um valor previamente abatido usando número do P Trab"""
        # Encontrar a transação pelo número do P Trab
        transacao_encontrada = None
        for transacao in self.transacoes:
            if transacao.get('numero_ptrab') == numero_ptrab and transacao['tipo'] == 'abatimento':
                transacao_encontrada = transacao
                break
        
        if not transacao_encontrada:
            return False, f"Transação não encontrada para P Trab {numero_ptrab}"
        
        valor_estorno = transacao_encontrada['valor']
        self.saldo_atual += valor_estorno
        
        transacao_estorno = {
            'id': f"ESTORNO_{numero_ptrab}",
            'numero_ptrab': numero_ptrab,
            'tipo': 'estorno',
            'valor': valor_estorno,
            'descricao': f"Estorno: {transacao_encontrada['descricao']}",
            'homologador': homologador,
            'data': datetime.now().isoformat(),
            'saldo_anterior': self.saldo_atual - valor_estorno,
            'saldo_posterior': self.saldo_atual
        }
        
        self.transacoes.append(transacao_estorno)
        self.save_saldo()
        
        return True, f"Valor de R$ {valor_estorno:,.2f} estornado com sucesso para P Trab {numero_ptrab}. Novo saldo: {self.get_saldo_formatado()}"
    
    def get_extrato(self, limite=50):
        """Retorna o extrato das transações"""
        return self.transacoes[-limite:] if self.transacoes else []
    
    def resetar_saldo(self, homologador):
        """Reseta o saldo para o valor inicial (apenas para administração)"""
        saldo_anterior = self.saldo_atual
        self.saldo_atual = self.saldo_inicial
        
        transacao = {
            'id': 'RESET',
            'tipo': 'reset',
            'valor': self.saldo_inicial - saldo_anterior,
            'descricao': 'Reset administrativo do saldo',
            'homologador': homologador,
            'data': datetime.now().isoformat(),
            'saldo_anterior': saldo_anterior,
            'saldo_posterior': self.saldo_atual
        }
        
        self.transacoes.append(transacao)
        self.save_saldo()
        
        return True, f"Saldo resetado para {self.get_saldo_formatado()}"

# Instância global do gerenciador de saldo
saldo_manager = SaldoManager()