      
-- Exclui a tabela caso ela exista
DROP TABLE IF EXISTS registros_chaves;

-- Cria uma tabela para armazenar os registros de chaves com informações sobre quem requisita.

CREATE TABLE registros_chaves (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome_responsavel TEXT NOT NULL,      
    telefone TEXT,
    empresa TEXT,
    codigo_empresa TEXT,
    nome_chave TEXT NOT NULL,            
    data_hora_retirada DATETIME NOT NULL, 
    data_hora_devolucao DATETIME,        
    observacoes TEXT                    
);

    


