-- Non serve eseguirlo a mano: la tabella viene creata in automatico alla prima richiesta.
-- Utile solo se vuoi crearla in anticipo:  npx wrangler d1 execute soullink --remote --file=schema.sql
CREATE TABLE IF NOT EXISTS partita (
  id TEXT PRIMARY KEY,
  stato TEXT NOT NULL,
  versione INTEGER NOT NULL,
  aggiornato INTEGER NOT NULL
);

-- Per ricominciare tutto da zero (cancella la partita!):
-- DELETE FROM partita;
