-- Script SQL para adicionar a coluna last_login_at na tabela users
-- Execute este script no banco de produção se a coluna não existir

-- Verifica se a coluna existe antes de adicionar
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'users' 
        AND column_name = 'last_login_at'
    ) THEN
        ALTER TABLE users 
        ADD COLUMN last_login_at TIMESTAMP WITH TIME ZONE NULL;
        
        RAISE NOTICE 'Coluna last_login_at adicionada com sucesso!';
    ELSE
        RAISE NOTICE 'Coluna last_login_at já existe!';
    END IF;
END $$;



