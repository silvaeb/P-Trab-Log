import os
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.units import mm
from datetime import datetime, timedelta
import math
import re
import locale
import json
import pandas as pd

class GeradorPDFPTrab:
    def __init__(self):
        self.styles = getSampleStyleSheet()
        
        # Configurar encoding para suportar caracteres especiais
        import reportlab.rl_config
        reportlab.rl_config.warnOnMissingFontGlyphs = 0
        
        self.setup_styles()
        
        # Configurar locale para formato brasileiro
        try:
            locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
        except:
            try:
                locale.setlocale(locale.LC_ALL, 'Portuguese_Brazil.1252')
            except:
                pass
    
    def setup_styles(self):
        """Configura os estilos para o documento"""
        # Estilo para cabeçalho
        self.styles.add(ParagraphStyle(
            name='Header',
            parent=self.styles['Normal'],
            fontSize=12,
            textColor=colors.black,
            alignment=1,  # Centro
            spaceAfter=6,
            fontName='Helvetica-Bold'
        ))
        
        # Estilo para número de controle
        self.styles.add(ParagraphStyle(
            name='NumeroControle',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.black,
            alignment=1,  # Centro
            spaceAfter=6,
            fontName='Helvetica-Bold'
        ))
        
        # Estilo para subtítulo
        self.styles.add(ParagraphStyle(
            name='Subheader',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.black,
            alignment=1,  # Centro
            spaceAfter=3,
            fontName='Helvetica'
        ))
        
        # Estilo para células da tabela com texto justificado
        self.styles.add(ParagraphStyle(
            name='CellJustified',
            parent=self.styles['Normal'],
            fontSize=6,
            textColor=colors.black,
            alignment=4,  # Justificado
            spaceAfter=0,
            fontName='Helvetica',
            wordWrap='CJK'
        ))
        
        # Estilo para células centradas
        self.styles.add(ParagraphStyle(
            name='CellCenter',
            parent=self.styles['Normal'],
            fontSize=6,
            textColor=colors.black,
            alignment=1,  # Centro
            spaceAfter=0,
            fontName='Helvetica'
        ))
        
        # Estilo para células com quebra automática
        self.styles.add(ParagraphStyle(
            name='CellWrap',
            parent=self.styles['Normal'],
            fontSize=6,
            textColor=colors.black,
            alignment=4,  # Justificado
            spaceAfter=0,
            fontName='Helvetica',
            wordWrap='CJK'
        ))
        
        # Estilo para memória de cálculo
        self.styles.add(ParagraphStyle(
            name='Memoria',
            parent=self.styles['Normal'],
            fontSize=5,
            textColor=colors.black,
            alignment=4,  # Justificado
            spaceAfter=1,
            fontName='Helvetica'
        ))
        
        # Estilo para assinatura
        self.styles.add(ParagraphStyle(
            name='Assinatura',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.black,
            alignment=1,  # Centro
            spaceAfter=2,
            fontName='Helvetica-Bold'
        ))
        
        # Estilo para função
        self.styles.add(ParagraphStyle(
            name='Funcao',
            parent=self.styles['Normal'],
            fontSize=9,
            textColor=colors.black,
            alignment=1,  # Centro
            spaceAfter=0,
            fontName='Helvetica'
        ))

    def obter_numero_controle(self):
        """Obtém o próximo número de controle sequencial por ano"""
        ano_atual = datetime.now().year
        arquivo_controle = 'controle_ptrab.json'
        
        try:
            if os.path.exists(arquivo_controle):
                with open(arquivo_controle, 'r') as f:
                    controle = json.load(f)
            else:
                controle = {}
            
            if str(ano_atual) not in controle:
                controle[str(ano_atual)] = 1
            else:
                controle[str(ano_atual)] += 1
            
            # SALVAR ANTES DE RETORNAR para garantir consistência
            with open(arquivo_controle, 'w') as f:
                json.dump(controle, f)
            
            numero = controle[str(ano_atual)]
            return f"P Trab Nr {numero:05d}/{ano_atual}"
            
        except Exception as e:
            print(f"Erro ao gerar número de controle: {e}")
            # Em caso de erro, usar timestamp como fallback
            timestamp = datetime.now().strftime("%H%M%S")
            return f"P Trab Nr {timestamp}/{ano_atual}"

    def criar_cabecalho_com_brasao(self, dados_cabecalho, numero_controle=None):
        """Cria o cabeçalho do documento com brasão da república"""
        # Se não foi passado um número de controle, gerar um novo
        if numero_controle is None:
            numero_controle = self.obter_numero_controle()
        
        # Tente carregar o brasão da pasta "P Trab"
        brasao = None
        brasao_paths = [
            os.path.join('P Trab', 'brasao_republica.png'),
            os.path.join('P Trab', 'brasao_republica.jpg'),
            'brasao_republica.png',
            'brasao_republica.jpg'
        ]
        
        for path in brasao_paths:
            try:
                if os.path.exists(path):
                    brasao = Image(path, width=30*mm, height=30*mm)  # Tamanho ajustado
                    print(f"✅ Brasão carregado: {path}")
                    break
            except:
                continue
        
        # Tabela com brasão e texto
        if brasao:
            cabecalho_data = [
                [brasao],  # Brasão centralizado acima
                ["MINISTÉRIO DA DEFESA"],
                ["EXÉRCITO BRASILEIRO"],
                [dados_cabecalho['unidade']],
                [dados_cabecalho['titulo_unidade']],
                [Paragraph("<u>PLANO DE TRABALHO LOGÍSTICO</u>", self.styles['Header'])],  # Sublinhado
                [Paragraph(numero_controle, self.styles['NumeroControle'])]  # Número de controle
            ]
            
            estilo_cabecalho = TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 1), (-1, -1), 12),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                ('LEFTPADDING', (0, 0), (-1, -1), 10),
                ('RIGHTPADDING', (0, 0), (-1, -1), 10),
            ])
            
            tabela_cabecalho = Table(cabecalho_data, colWidths=[200*mm])
            tabela_cabecalho.setStyle(estilo_cabecalho)
        else:
            # Fallback sem brasão
            print("⚠️  Brasão não encontrado, usando cabeçalho sem imagem")
            cabecalho_data = [
                ["MINISTÉRIO DA DEFESA"],
                ["EXÉRCITO BRASILEIRO"],
                [dados_cabecalho['unidade']],
                [dados_cabecalho['titulo_unidade']],
                [Paragraph("<u>PLANO DE TRABALHO LOGÍSTICO</u>", self.styles['Header'])],
                [Paragraph(numero_controle, self.styles['NumeroControle'])]
            ]
            
            estilo_cabecalho = TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 12),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                ('LEFTPADDING', (0, 0), (-1, -1), 10),
                ('RIGHTPADDING', (0, 0), (-1, -1), 10),
            ])
            
            tabela_cabecalho = Table(cabecalho_data, colWidths=[200*mm])
            tabela_cabecalho.setStyle(estilo_cabecalho)
        
        return [tabela_cabecalho, Spacer(1, 5*mm)]

    def criar_rodape(self, local, militar, funcao):
        """Cria o rodape do documento com local, data e assinatura"""
        # Data atual no formato brasileiro
        data_atual = datetime.now().strftime('%d/%m/%Y')
        
        rodape_data = [
            [f"{local}, {data_atual}"],
            [Paragraph(militar, self.styles['Assinatura'])],
            [Paragraph(funcao, self.styles['Funcao'])]
        ]
        
        estilo_rodape = TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ('TOPPADDING', (0, 1), (-1, 1), 10),  # Espaço para assinatura
        ])
        
        tabela_rodape = Table(rodape_data, colWidths=[180*mm])
        tabela_rodape.setStyle(estilo_rodape)
        
        return tabela_rodape

    def formatar_moeda(self, valor):
        """Formata valores monetários no padrão brasileiro"""
        try:
            return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        except:
            return f"R$ {valor:.2f}"

    def calcular_dias_operacao(self, periodo):
        """Calcula o número de dias automaticamente com base no período"""
        try:
            # Se período for numérico, retorna o próprio valor
            if isinstance(periodo, (int, float)):
                return int(periodo)
                
            # Se for string, faz o parsing das datas
            if not periodo or ' A ' not in periodo:
                return 30  # Valor padrão
                
            partes = periodo.split(' A ')
            if len(partes) != 2:
                return 30  # Valor padrão
                
            data_inicio = datetime.strptime(partes[0].strip(), '%d/%m/%Y')
            data_fim = datetime.strptime(partes[1].strip(), '%d/%m/%Y')
            
            # Inclui o dia de início e de término
            dias = (data_fim - data_inicio).days + 1
            return dias if dias > 0 else 30
        except:
            return 30  # Valor padrão em caso de erro

    def criar_info_operacao(self, dados_operacao):
     """Cria a seção de informações da operação COM QUEBRA AUTOMÁTICA DE TEXTO"""
    
     # Estilo para células com quebra automática
     cell_style = ParagraphStyle(
        name='CellWrap',
        parent=self.styles['Normal'],
        fontSize=8,
        textColor=colors.black,
        alignment=4,  # Justificado
        spaceAfter=0,
        fontName='Helvetica',
        wordWrap='CJK',  # Permite quebra de palavras
        leading=10,  # Espaçamento entre linhas
        splitLongWords=True,  # Quebra palavras longas
    )
    
     # Função para criar parágrafos com quebra automática
     def criar_paragrafo(texto, largura_maxima=140*mm):
        if not texto:
            texto = ""
        return Paragraph(str(texto), cell_style)
    
     info_data = [
        ["1. Nome da Operação", criar_paragrafo(dados_operacao['nome_operacao'])],
        ["2. Período", criar_paragrafo(dados_operacao['periodo'])],
        ["3. Local", criar_paragrafo(dados_operacao['local'])],
        ["4. Solicitante", criar_paragrafo(dados_operacao['solicitante'])],
        ["5. Descrição", criar_paragrafo(dados_operacao['descricao'])],
        ["6. Faseamento", criar_paragrafo(dados_operacao['faseamento'])],
        ["7. Composição dos meios", criar_paragrafo(dados_operacao['composicao_meios'])],
        ["8. Efetivo", criar_paragrafo(dados_operacao['efetivo_total'])]
    ]
    
     estilo_info = TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (0, -1), 8),  # Tamanho para coluna de labels
        ('FONTSIZE', (1, 0), (1, -1), 8),  # Tamanho para coluna de valores
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),  # Aumentado para melhor espaçamento
        ('TOPPADDING', (0, 0), (-1, -1), 6),     # Aumentado para melhor espaçamento
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),      # Labels alinhados à esquerda
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),      # Valores alinhados à esquerda
    ])
    
     # Ajustar altura das linhas baseado no conteúdo
     row_heights = []
     for label, value in info_data:
        # Estimar altura baseada no conteúdo (aproximação)
        text_content = str(value.getPlainText() if hasattr(value, 'getPlainText') else value)
        estimated_lines = max(1, len(text_content) // 60)  # ~60 caracteres por linha
        height = max(15, estimated_lines * 12)  # Mínimo 15mm, +12mm por linha extra
        row_heights.append(height)
    
     tabela_info = Table(info_data, colWidths=[35*mm, 145*mm], rowHeights=row_heights)
     tabela_info.setStyle(estilo_info)
    
     return tabela_info

    def criar_tabela_alimentacao(self, itens_alimentacao):
        """Cria a tabela principal de alimentação em formato paisagem - FORMATAÇÃO PADRÃO"""
        
        # VALIDAÇÃO: Garantir que todos os itens tenham a estrutura correta
        required_fields = ['odop_ods', 'gnd', 'ed', 'finalidade', 'om_uge_codug', 'codom', 
                          'quantidade_base', 'unidade_base', 'valor_unitario', 'quantidade_dias', 
                          'valor_total', 'natureza_despesa', 'descricao_memoria', 'formula', 
                          'calculo_detalhado', 'total_item']
        
        for item in itens_alimentacao:
            for field in required_fields:
                if field not in item:
                    item[field] = ""  # Ou valor padrão apropriado
                    print(f"⚠️  Campo {field} não encontrado no item, usando valor padrão")
        
        # Cabeçalho da tabela CORRIGIDO conforme modelo
        header = [
            "Classificação\nda Despesa",
            "ODOp/\nODS",
            "GND",
            "ED",
            "Finalidade",
            "OM (UGE)\nCODUG",
            "CODOM",
            "Qnt\nBASE",
            "Und\nBASE",
            "Valor\nunit (R$)",
            "Qnt\ndias",
            "Valor\ntotal (R$)",
            "Memória de Cálculo / Justificativas"
        ]
        
        data = [header]
        
        total_geral = 0
        
        # Adicionar itens
        for item in itens_alimentacao:
            linha = [
                Paragraph("Alimentação (Classe I)", self.styles['CellJustified']),
                Paragraph(item['odop_ods'], self.styles['CellCenter']),
                Paragraph(item['gnd'], self.styles['CellCenter']),
                Paragraph(item['ed'], self.styles['CellCenter']),
                Paragraph(item['finalidade'], self.styles['CellJustified']),
                Paragraph(item['om_uge_codug'], self.styles['CellJustified']),
                Paragraph(item['codom'], self.styles['CellCenter']),
                Paragraph(str(item['quantidade_base']), self.styles['CellCenter']),
                Paragraph(item['unidade_base'], self.styles['CellCenter']),
                Paragraph(self.formatar_moeda(item['valor_unitario']), self.styles['CellCenter']),
                Paragraph(str(item['quantidade_dias']), self.styles['CellCenter']),
                Paragraph(self.formatar_moeda(item['valor_total']), self.styles['CellCenter']),
                self.criar_memoria_calculo(item)
            ]
            data.append(linha)
            total_geral += item['valor_total']
        
        # Adicionar linha de total geral
        if itens_alimentacao:
            linha_total = [
                Paragraph("TOTAL GERAL", self.styles['CellJustified']),
                Paragraph("", self.styles['CellCenter']),
                Paragraph("", self.styles['CellCenter']),
                Paragraph("", self.styles['CellCenter']),
                Paragraph("", self.styles['CellCenter']),
                Paragraph("", self.styles['CellCenter']),
                Paragraph("", self.styles['CellCenter']),
                Paragraph("", self.styles['CellCenter']),
                Paragraph("", self.styles['CellCenter']),
                Paragraph("", self.styles['CellCenter']),
                Paragraph("", self.styles['CellCenter']),
                Paragraph(self.formatar_moeda(total_geral), self.styles['CellCenter']),
                Paragraph("", self.styles['CellCenter'])
            ]
            data.append(linha_total)
        
        # LARGURAS DAS COLUNAS CORRIGIDAS
        col_widths = [
            18*mm,  # Classificação da Despesa
            10*mm,  # ODOp/ODS
            8*mm,   # GND
            8*mm,   # ED
            25*mm,  # Finalidade
            22*mm,  # OM (UGE) CODUG
            12*mm,  # CODOM
            8*mm,   # Qnt BASE
            8*mm,   # Und BASE
            12*mm,  # Valor unit
            8*mm,   # Qnt dias
            15*mm,  # Valor total
            42*mm   # Memória de Cálculo
        ]
        
        estilo_tabela = TableStyle([
            # Estilo do cabeçalho
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 6),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
            
            # Estilo das células
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 6),
            ('VALIGN', (0, 1), (-1, -1), 'TOP'),
            
            # Grid
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
            ('TOPPADDING', (0, 0), (-1, -1), 1),
            ('LEFTPADDING', (0, 0), (-1, -1), 2),
            ('RIGHTPADDING', (0, 0), (-1, -1), 2),
            
            # Estilo para linha do total
            ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, -1), (-1, -1), 7),
        ])
        
        tabela = Table(data, colWidths=col_widths, repeatRows=1)
        tabela.setStyle(estilo_tabela)
        
        return tabela

    def criar_memoria_calculo(self, item):
        """Cria o texto da memória de cálculo formatado corretamente"""
        memoria = f"<b>{item['natureza_despesa']}</b><br/>"
        memoria += f"{item['descricao_memoria']}<br/>"
        memoria += f"<b>DETALHAMENTO/ MEMÓRIA DE CÁLCULO</b><br/>"
        memoria += f"{item['formula']}<br/>"
        
        # Dividir o cálculo detalhado em linhas menores se for muito longo
        calculo_lines = item['calculo_detalhado'].split('\n')
        for line in calculo_lines:
            if line.strip():
                memoria += f"→ {line.strip()}<br/>"
        
        memoria += f"<b>{item['total_item']}</b>"
        
        return Paragraph(memoria, self.styles['Memoria'])

    def validar_codug(self, codug):
        """Valida CODUG - 6 dígitos numéricos começando com 160"""
        if not codug:
            return ""
        # Remove caracteres não numéricos
        codug_limpo = re.sub(r'\D', '', codug)
        # Limita a 6 dígitos
        codug_limpo = codug_limpo[:6]
        # Valida que começa com 160
        if len(codug_limpo) >= 3 and not codug_limpo.startswith('160'):
            raise ValueError("CODUG deve começar com 160")
        return codug_limpo

    def validar_codom(self, codom):
        """Valida CODOM - até 5 dígitos numéricos"""
        if not codom:
            return ""
        # Remove caracteres não numéricos
        codom_limpo = re.sub(r'\D', '', codom)
        # Limita a 5 dígitos
        return codom_limpo[:5]

    def calcular_valores_emprego(self, efetivo, dias_operacao, refeicoes_intermediarias, tipo):
        """Calcula os valores para operações de EMPREGO conforme nova diretriz com limite de 8 dias"""
        if tipo == 'QR':
            valor_etapa = 7.00  # Valor do QR
            valor_unitario = 2.33
        else:  # QS
            valor_etapa = 10.00  # Valor do QS
            valor_unitario = 3.33
            
        valor_ref_intr = valor_etapa / 3
        
        if dias_operacao <= 22:
            # Fórmula para operações ≤ 22 dias
            valor_total = efetivo * refeicoes_intermediarias * valor_ref_intr * dias_operacao
            
        else:
            # Fórmula para operações > 22 dias com limite de 8 dias
            dias_ate_22 = 22
            dias_apos_22 = min(dias_operacao - 22, 8)  # LIMITE DE 8 DIAS
            dias_excedentes = max(dias_operacao - 30, 0)  # Dias além de 30
            
            if dias_operacao <= 30:
                # Operação entre 23 e 30 dias
                valor_total = (efetivo * refeicoes_intermediarias * valor_ref_intr * dias_ate_22 +
                             efetivo * valor_etapa * dias_apos_22)
            else:
                # Operação com mais de 30 dias (múltiplos períodos)
                # Primeiro período: 30 dias (22 + 8)
                valor_primeiro_periodo = (efetivo * refeicoes_intermediarias * valor_ref_intr * dias_ate_22 +
                                        efetivo * valor_etapa * 8)
                
                # Períodos adicionais completos de 30 dias
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
                
                valor_total = valor_primeiro_periodo + valor_periodos_completos + valor_periodo_parcial
        
        return valor_total, valor_unitario

    def calcular_valores_preparo(self, efetivo, dias_operacao, tipo):
        """Calcula os valores para operações de PREPARO conforme nova diretriz com limite de 8 dias"""
        if tipo == 'QR':
            valor_etapa_especifica = 7.00  # QR
            valor_complemento_especifico = 1.40  # 20% de R$6,00
        else:  # QS
            valor_etapa_especifica = 10.00  # QS
            valor_complemento_especifico = 2.00  # 20% de R$9,00
        
        if dias_operacao <= 22:
            # Fórmula para operações ≤ 22 dias
            valor_total = efetivo * valor_complemento_especifico * dias_operacao
            valor_unitario = valor_complemento_especifico
            
        else:
            # Fórmula para operações > 22 dias com limite de 8 dias
            dias_ate_22 = 22
            dias_apos_22 = min(dias_operacao - 22, 8)  # LIMITE DE 8 DIAS
            dias_excedentes = max(dias_operacao - 30, 0)  # Dias além de 30
            
            if dias_operacao <= 30:
                # Operação entre 23 e 30 dias
                valor_total = (efetivo * valor_complemento_especifico * dias_ate_22 +
                             efetivo * valor_etapa_especifica * dias_apos_22 +
                             efetivo * valor_complemento_especifico * dias_apos_22)
            else:
                # Operação com mais de 30 dias (múltiplos períodos)
                # Primeiro período: 30 dias (22 + 8)
                valor_primeiro_periodo = (efetivo * valor_complemento_especifico * dias_ate_22 +
                                        efetivo * valor_etapa_especifica * 8 +
                                        efetivo * valor_complemento_especifico * 8)
                
                # Períodos adicionais completos de 30 dias
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
                
                valor_total = valor_primeiro_periodo + valor_periodos_completos + valor_periodo_parcial
            
            valor_unitario = valor_complemento_especifico
        
        return valor_total, valor_unitario

    def gerar_calculo_detalhado_emprego(self, efetivo, dias_operacao, refeicoes_intermediarias, tipo):
        """Gera o cálculo detalhado formatado corretamente para EMPREGO"""
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

    def gerar_calculo_detalhado_preparo(self, efetivo, dias_operacao, tipo):
        """Gera o cálculo detalhado para operações de PREPARO com limite de 8 dias"""
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

    # ... (restante do código permanece igual)

def modo_interativo():
    """Modo interativo para inserir dados da operação"""
    gerador = GeradorPDFPTrab()
    
    print("GERADOR DE PLANO DE TRABALHO - ALIMENTAÇÃO CLASSE I")
    print("=" * 60)
    
    # Seleção do tipo de operação
    print("\nSELECIONE O TIPO DE OPERAÇÃO:")
    print("1 - OPERAÇÃO DE EMPREGO")
    print("2 - OPERAÇÃO DE PREPARO")
    
    tipo_operacao = input("Digite 1 ou 2: ")
    while tipo_operacao not in ['1', '2']:
        print("Opção inválida! Digite 1 ou 2.")
        tipo_operacao = input("Digite 1 ou 2: ")
    
    tipo_operacao_nome = "EMPREGO" if tipo_operacao == '1' else "PREPARO"
    print(f"\nTipo de operação selecionado: {tipo_operacao_nome}")
    
    # Coletar dados do cabeçalho
    print("\nDADOS DO CABEÇALHO:")
    dados_cabecalho = {}
    dados_cabecalho['unidade'] = input("Unidade (ex: 15ª BRIGADA DE INFANTARIA MECANIZADA): ") or "15ª BRIGADA DE INFANTARIA MECANIZADA"
    dados_cabecalho['titulo_unidade'] = input("Título da Unidade (ex: BRIGADA POTÊNCIA DO OESTE): ") or "BRIGADA POTÊNCIA DO OESTE"
    
    # Coletar dados da operação
    print("\nINFORMAÇÕES DA OPERAÇÃO:")
    dados_operacao = {}
    dados_operacao['nome_operacao'] = input("1. Nome da Operação: ") or "OP PUNHOS DE AÇO"
    
    # Período com cálculo automático de dias
    periodo = input("2. Período (ex: 12/10/2025 A 25/11/2025): ") or "12/10/2025 A 25/11/2025"
    dados_operacao['periodo'] = periodo
    dias_operacao = gerador.calcular_dias_operacao(periodo)
    print(f"   Dias calculados automaticamente: {dias_operacao} dias")
    
    dados_operacao['local'] = input("3. Local: ") or "Francisco Beltrão-PR"
    dados_operacao['solicitante'] = input("4. Solicitante: ") or "Comando Militar do Sul"
    dados_operacao['descricao'] = input("5. Descrição: ") or "Realizar Reconhecimento de Eixo"
    dados_operacao['faseamento'] = input("6. Faseamento: ") or "PAA"
    dados_operacao['composicao_meios'] = input("7. Composição dos meios: ") or "OM da 15ª Bda Inf Mec"
    dados_operacao['efetivo_total'] = input("8. Efetivo total: ") or "2200"
    
    # Coletar dados do rodape (assinatura)
    print("\nDADOS PARA ASSINATURA:")
    local_emissao = input("Local de emissão do documento: ") or "Francisco Beltrão-PR"
    
    nome_militar = input("Nome do militar (ex: JOÃO DA SILVA): ").upper() or "MILITAR RESPONSÁVEL"
    posto = input("Posto/Graduação (ex: TEN CEL): ") or "RESPONSÁVEL"
    militar_assina = f"{nome_militar} - {posto}"
    
    funcao_militar = input("Função do militar: ") or "Responsável pelo Plano de Trabalho"
    
    # Coletar itens de alimentação
    itens_alimentacao = []
    print("\nADICIONAR ITENS DE ALIMENTAÇÃO:")
    print("=" * 60)
    
    while True:
        print(f"\nItem {len(itens_alimentacao) + 1}:")
        tipo = input("Tipo (QR/QS): ").upper().strip()
        if tipo not in ['QR', 'QS']:
            print("Tipo inválido! Use QR ou QS.")
            continue
            
        efetivo = int(input("Efetivo: "))
        
        # Usar dias calculados automaticamente
        dias = dias_operacao
        print(f"Dias da operação: {dias} (calculado automaticamente)")
        
        # OM será informada aqui
        om = input("OM (Organização Militar): ")
        
        # Validar CODUG (6 dígitos começando com 160)
        while True:
            codug_input = input("CODUG (6 dígitos começando com 160, ex: 160238): ")
            try:
                codug = gerador.validar_codug(codug_input)
                if len(codug) != 6:
                    print("ERRO: CODUG deve ter exatamente 6 dígitos")
                    continue
                print(f"CODUG validado: {codug}")
                break
            except ValueError as e:
                print(f"ERRO: {e}")
        
        # Validar CODOM (5 dígitos)
        while True:
            codom_input = input("CODOM (até 5 dígitos): ")
            codom = gerador.validar_codom(codom_input)
            if codom:
                print(f"CODOM validado: {codom}")
                break
            else:
                print("ERRO: CODOM deve conter apenas números")
        
        # Definir finalidade automaticamente baseada no tipo
        if tipo == 'QS':
            finalidade = "Quantitativo de Subsistência (QS)"
        else:  # QR
            finalidade = "Quantitativo de Rancho (QR)"
        
        # Calcular valores conforme o tipo de operação
        if tipo_operacao == '1':  # EMPREGO
            ref_intr = int(input("Refeições intermediárias (1-3): ") or "2")
            valor_total, valor_unitario = gerador.calcular_valores_emprego(efetivo, dias, ref_intr, tipo)
            calculo_detalhado = gerador.gerar_calculo_detalhado_emprego(efetivo, dias, ref_intr, tipo)
            
            if dias <= 22:
                formula = 'Fórmula: Efetivo empregado x nº Ref Itr (máximo de 03) x Valor da etapa/3 x Nr de dias'
            else:
                formula = 'Fórmula: Efetivo empregado x nº Ref Itr (máximo de 03) x Valor da etapa/3 x 22 dias + Efetivo empregado x Valor da etapa x Nr dias após 22 (até 8 dias)'
            
        else:  # PREPARO
            valor_total, valor_unitario = gerador.calcular_valores_preparo(efetivo, dias, tipo)
            calculo_detalhado = gerador.gerar_calculo_detalhado_preparo(efetivo, dias, tipo)
            
            if dias <= 22:
                formula = 'Fórmula: Efetivo empregado x Complemento de Operação (20%) x Nr de dias até 22 dias'
            else:
                formula = 'Fórmula: Efetivo empregado x Complemento de Operação (20%) x 22 dias + Efetivo empregado x Valor da etapa x Nr dias após 22 (até 8 dias) + Efetivo empregado x Complemento de Operação (20%) x Nr dias após 22 (até 8 dias)'

        # Formatar valores para o padrão brasileiro
        valor_total_formatado = gerador.formatar_moeda(valor_total)
        
        # Formatar o cálculo detalhado com valores monetários formatados
        calculo_detalhado_formatado = calculo_detalhado
        valores = re.findall(r'R\$\s*(\d+\.?\d*)', calculo_detalhado)
        for valor in valores:
            try:
                valor_float = float(valor)
                valor_formatado = gerador.formatar_moeda(valor_float)
                calculo_detalhado_formatado = calculo_detalhado_formatado.replace(f"R$ {valor}", valor_formatado)
            except:
                pass
        
        item = {
            'odop_ods': 'COLOG',
            'gnd': '3',
            'ed': '30',
            'finalidade': finalidade,
            'om_uge_codug': f'{om} ({codug})' if codug else om,
            'codom': codom,
            'quantidade_base': efetivo,
            'unidade_base': 'H/dia',
            'valor_unitario': valor_unitario,
            'quantidade_dias': dias,
            'valor_total': valor_total,
            'natureza_despesa': f'33.90.30 - Aquisição de gêneros alimentícios ({tipo}) para 01 (uma) refeição intermediária' if tipo_operacao == '1' else f'33.90.30 - Aquisição de gêneros alimentícios ({tipo})',
            'descricao_memoria': f'destinada à complementação de alimentação de {efetivo} militares durante {dias} dias',
            'formula': formula,
            'calculo_detalhado': calculo_detalhado_formatado,
            'total_item': f'TOTAL {tipo}: {valor_total_formatado}'
        }
        
        itens_alimentacao.append(item)
        
        continuar = input("\nAdicionar outro item? (s/n): ").lower()
        if continuar != 's':
            break
    
    # Preparar dados para assinatura
    dados_assinatura = {
        'local': local_emissao,
        'militar': militar_assina,
        'funcao': funcao_militar
    }
    
    # Gerar visualização prévia
    print("\n" + "="*60)
    print("GERAR VISUALIZAÇÃO PRÉVIA?")
    print("="*60)
    gerar_previa = input("Deseja gerar uma visualização prévia antes do PDF? (s/n): ").lower()
    
    if gerar_previa == 's':
        gerador.gerar_previa_pdf(dados_cabecalho, dados_operacao, itens_alimentacao, dados_assinatura)
        
        confirmar = input("\nDeseja gerar o PDF final? (s/n): ").lower()
        if confirmar != 's':
            print("Geração do PDF cancelada.")
            return
    
    # Gerar nome do arquivo automaticamente baseado na unidade
    nome_unidade_limpo = re.sub(r'[^\w\s]', '', dados_cabecalho['unidade'])
    nome_unidade_arquivo = nome_unidade_limpo.replace(" ", "_").upper()
    nome_arquivo = f"P_TRAB_{nome_unidade_arquivo}.pdf"
    
    print(f"\nNome do arquivo PDF gerado automaticamente: {nome_arquivo}")
    
    # Criar o PDF diretamente
    try:
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
        from reportlab.lib.units import mm
        
        # Criar documento com margens de 2cm
        doc = SimpleDocTemplate(
            nome_arquivo,
            pagesize=landscape(A4),
            rightMargin=20*mm,   # 2cm
            leftMargin=20*mm,    # 2cm
            topMargin=20*mm,     # 2cm
            bottomMargin=20*mm   # 2cm
        )
        
        story = []
        
        # Cabeçalho com brasão
        story.extend(gerador.criar_cabecalho_com_brasao(dados_cabecalho))
        story.append(Spacer(1, 5*mm))
        
        # Informações da operação
        story.append(gerador.criar_info_operacao(dados_operacao))
        story.append(Spacer(1, 5*mm))
        
        # Tabela de alimentação
        items_por_pagina = 5
        total_itens = len(itens_alimentacao)
        
        for i in range(0, total_itens, items_por_pagina):
            if i > 0:
                # Adicionar quebra de página
                story.append(PageBreak())
                story.extend(gerador.criar_cabecalho_com_brasao(dados_cabecalho))
                story.append(Spacer(1, 5*mm))
            
            itens_pagina = itens_alimentacao[i:i + items_por_pagina]
            tabela_pagina = gerador.criar_tabela_alimentacao(itens_pagina)
            story.append(tabela_pagina)
        
        # Adicionar rodape na última página
        story.append(Spacer(1, 10*mm))
        story.append(gerador.criar_rodape(local_emissao, militar_assina, funcao_militar))
        
        # Gerar PDF
        doc.build(story)
        
        print(f"✅ PDF gerado com sucesso: {nome_arquivo}")
        print(f"\nOperação de {tipo_operacao_nome} processada com sucesso!")
        
    except Exception as e:
        print(f"❌ Erro ao gerar PDF: {e}")
        print("Verifique se o arquivo não está aberto em outro programa.")

if __name__ == "__main__":
    modo_interativo()