import xmlrpc.client
import pandas as pd

# 1. Configurare conexiune Odoo
URL = ""
DB = "" # De obicei se află în URL sau la login
USER = ""
PASSWORD = "" # Recomandat API Key pentru securitate

# Conectarea la server
common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(URL))
uid = common.authenticate(DB, USER, PASSWORD, {})

if not uid:
    print("Autentificare eșuată!")
    exit()

models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(URL))

# 2. Găsirea ID-ului pentru stadiul MKTR
# Presupunem că pipeline-ul se aplică echipei tale, căutăm după nume.
stage_ids = models.execute_kw(DB, uid, PASSWORD,
    'crm.stage', 'search',
    [[['name', '=', 'MKTR']]]
)
if not stage_ids:
    print("Stadiul 'MKTR' nu a fost găsit. Verifică numele exact.")
    exit()
mktr_stage_id = stage_ids[0]
# --- COD NOU: Căutăm ID-urile tag-urilor dorite ---
nume_taguri = ['iGV', 'Cluj-Napoca']
tag_ids = models.execute_kw(DB, uid, PASSWORD, 'crm.tag', 'search', [[['name', 'in', nume_taguri]]])

if not tag_ids:
    print("Atenție: Tag-urile nu au fost găsite! Verifică scrierea lor.")

# 3. Citirea datelor din Excel
# Înlocuiește 'leaduri.xlsx' cu calea către fișierul tău
df = pd.read_excel('leaduri.xlsx', nrows=300)

# 4. Procesarea și importul fiecărui lead
for index, row in df.iterrows():
    # 1. Verificăm mai întâi dacă există număr de telefon
    telefon_raw = row['Telefon']
    judet = str(row['Judet']).strip().upper()
    
    # 2. Dacă nu este din Maramureș (MM), sărim peste acest rând
    if judet != 'MM':
        print(f"Lead sărit (nu este din MM): {row['Nume Lead']}")
        continue
    
    # Dacă celula este goală (NaN) sau conține doar spații, sărim peste acest lead
    if pd.isna(telefon_raw) or str(telefon_raw).strip() == "":
        print(f"Lead sărit (fără număr de telefon): {row['Nume Lead']}")
        continue # Trecem direct la următorul rând din Excel
    
    # 2. Dacă am ajuns aici, înseamnă că avem un telefon valid
    telefon_val = str(telefon_raw).strip()
    
    nume_baza = str(row['Nume Lead']).strip()
    judet = str(row['Judet']).strip()
    email_val = str(row['Email']).strip() if pd.notna(row['Email']) else False
    
    nume_final = f"{nume_baza}_GV_{judet}"
    
    # Crearea lead-ului în Odoo
    lead_id = models.execute_kw(DB, uid, PASSWORD, 'crm.lead', 'create', [{
        'name': nume_final,
        'type': 'opportunity', 
        'stage_id': mktr_stage_id,
        'email_from': email_val,
        'phone': telefon_val,
        'tag_ids': [(6, 0, tag_ids)]
    }])
    
    print(f"Lead creat: {nume_final} (ID: {lead_id})")
    
    # 5. Adăugarea SPIN-ului ca Log Note (Mesaj intern)
    s_val = str(row['S']) if pd.notna(row['S']) else "N/A"
    p_val = str(row['P']) if pd.notna(row['P']) else "N/A"
    i_val = str(row['I']) if pd.notna(row['I']) else "N/A"
    n_val = str(row['N']) if pd.notna(row['N']) else "N/A"
    
    spin_note = f"""
        <p>S: {s_val}</p>
        <p>P: {p_val}</p>
        <p>I: {i_val}</p>
        <p>N: {n_val}</p>
    """
    
    models.execute_kw(DB, uid, PASSWORD, 'mail.message', 'create', [{
        'model': 'crm.lead',
        'res_id': lead_id,
        'body': spin_note,
        'message_type': 'comment',
        'subtype_id': 2
    }])