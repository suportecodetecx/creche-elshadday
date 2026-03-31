# services/unidades_config.py
# Configuração das unidades da Creche El Shadday

UNIDADES = {
    "CEIC El Shadday": {
        "nome": "CEIC El Shadday",
        "endereco": "Rua Francisco Vilani Bicudo, 470",
        "bairro": "Vila Nova Aparecida",
        "cidade": "Mogi das Cruzes",
        "uf": "SP",
        "cep": "08830-340",  # Ajustar conforme CEP real
        "cnpj": "03.067.526/0001-87",
        "telefone": "(11) 4739-3549",  # Ajustar
        "INEP": "35195340", 
        
    },
    
    "CEIM Prof. Egberto Malta Moreira": {
        "nome": "CEIM Prof. Egberto Malta Moreira",
        "endereco": "Rua Ten. Agenor Bertini, 202",
        "bairro": "Vila Rei",
        "cidade": "Mogi das Cruzes",
        "uf": "SP",
        "cep": "08717-875",  # Ajustar conforme CEP real
        "cnpj": "03.067.526/0002-68",
        "telefone": "(11) 4726-6241",  # Ajustar
       "INEP": "35195340",
        
    }
}

def get_unidade_info(nome_unidade):
    """Retorna as informações de uma unidade pelo nome"""
    return UNIDADES.get(nome_unidade, UNIDADES["CEIC El Shadday"])  # Fallback para CEIC