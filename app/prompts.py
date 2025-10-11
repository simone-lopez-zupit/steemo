
IMAGE_DESCRIPTION_PROMPT = (
    "In massimo due frasi. Indica funzionalità, azioni, input o opzioni presenti. "
    "Evita dettagli grafici, colori o layout puramente visivi."
)

# TASK_SIMILARITY_PROMPT_TEMPLATE = lambda target_text, candidate_text: (
#     "Confronta tecnicamente due task Jira ignorando completamente dominio, contesto specifico e posizione UI. "
#     "Valuta SOLO il livello tecnico dell’attività e la reale complessità implementativa.\n\n"
#     "Rispondi `true` esclusivamente se i due task condividono:\n"
#     "- Stessa tipologia tecnica (es. entrambi sono liste articolate, entrambi form complessi, "
#     "entrambi integrazioni API, entrambi setup o refactor significativi).\n"
#     "- Complessità simile (numero di elementi da gestire, presenza di interazioni utente, "
#     "livello di struttura dati coinvolta).\n"
#     "- Impegno operativo equivalente.\n\n"
#     "Se uno dei due è significativamente più semplice, come un form in sola lettura già fatto, "
#     "mentre l’altro implica strutture articolate o interazioni più complesse, rispondi sempre `false`.\n\n"
#     f"---\nPRIMO TASK:\n{target_text}\n\n"
#     f"---\nSECONDO TASK:\n{candidate_text}\n\n"
#     "Rispondi solo con `true` o `false`, minuscolo, senza spiegazioni."
# )
TASK_SIMILARITY_PROMPT_TEMPLATE = lambda target_text, candidate_text: (
    "Confronta tecnicamente questi due task Jira, ignorando completamente il contesto o il dominio. "
    "Valuta solo *cosa* viene chiesto di sviluppare, non *per chi* o *in che ambito*.\n"
    "Rispondi `true` solo se i due task richiedono lo sviluppo di funzionalità simili, con simile sforzo implementativo.\n"
    "---\nPRIMO TASK:\n"
    f"{target_text}\n\n"
    "---\nSECONDO TASK:\n"
    f"{candidate_text}\n\n"
    "Rispondi solo con `true` o `false`, minuscolo, senza spiegazioni."
    "Due task simili possono essere ad esempio entrambi liste complesse, entrambi form articolati, entrambi integrazioni API, filtri, setup, refactor significativi, modifica ui, modifica logiche, modifica labels, implementazione di endpoint "
)



STORY_POINT_PROMPT = (
    "Sei un assistente agile. Dato il testo di una user story, restituisci lo story point corretto "
    "in scala di Fibonacci ovvero compreso in questa lista [0.5, 1, 2, 3, 5, 8, 13, 21]"
)
STORY_POINT_PROMPT_few_shots = lambda target_text:(
    """
    "Sei un assistente agile. Dato il testo di una user story, restituisci lo story point corretto "
    "in scala di Fibonacci ovvero compreso in questa lista [0.5, 1, 2, 3, 5, 8, 13, 21] "
    "ecco alcuni esempi con i relativi storypoints "
    {"messages": [{"role": "system", "content": "Sei un assistente agile. Dato il testo di una user story, restituisci solo lo story point corretto in scala di Fibonacci (es. 0.5, 1, 2, 3, 5, 8, 13, 21)."}, {"role": "user", "content": "Come admin voglio filtrare i dati in base a se NON HANNO il SEGMENTO OPERATIVO\nInoltre, manca ancora la possibilità di selezione dei valori “null” nel filtro del segmento operativo\n\n\n\n\nClienti > Ubicazioni\n\n\nClienti > Utenti > modifica utente\n\n\nClienti > Utenti > creazione utente\n\n\nCommesse > Ubicazioni"}, {"role": "assistant", "content": "2"}]}

    "\n\nRICORDA DEVI RISPONDERE SOLO CON UN NUMERO PRESENTE in scala di Fibonacci ovvero compreso in questa lista [0.5, 1, 2, 3, 5, 8, 13, 21]"
    "\nTARGET  story:\n"
    """
    + target_text
)

# STORY_POINT_PROMPT_WITH_TEXT=(
#     "Sei un assistente agile. Dato il testo di una user story, restituisci lo story point corretto "
#     "in scala di Fibonacci ovvero compreso in questa lista [0.5, 1, 2, 3, 5, 8, 13, 21] seguito da una motivazione tecnica della scelta, "
#     "indicando i fattori che impattano lo sforzo di sviluppo: complessità, numero di funzionalità, input utente, "
#     "dipendenze esterne, o altro."
#     "potrebbe essere presente una sezione 'comandi' nel quale sarà possibile aggiungere o rimuovere complessità"

# )
# STORY_POINT_PROMPT_WITH_TEXT = (
#     """Sei un assistente agile. A partire dal testo di una user story e dagli story point assegnati, 
#     fornisci SEMPRE e OBBLIGATORIAMENTE due elementi:

#     1. Una breve descrizione tecnica (massimo 20 parole).
#     2. Una lista sintetica dei fattori che influenzano la complessità della user story.

#     Rispetta rigorosamente il seguente formato JSON:
#     {
#         "descrizione": "<descrizione tecnica breve, obbligatoria>",
#         "lista_fattori": ["fattore1", "fattore2", "..."]
#     }
   
#     """
# )
STORY_POINT_PROMPT_WITH_TEXT = (
    """Sei un assistente agile. A partire dal testo di una user story e dagli story point assegnati, 
    fornisci SEMPRE e OBBLIGATORIAMENTE la seguente struttura JSON:

    1. Una breve descrizione tecnica (massimo 20 parole).
    

    Rispetta rigorosamente il seguente formato JSON:
    {
        "descrizione": "<descrizione tecnica breve, obbligatoria>",
    }
   
    """
)
ABSTRACT_SUMMARY_PROMPT = (
    "make a synthetic and abstract summary of what needs to be implemented in the task "
    "but without talking about the specific domain at all, you have to extract only the complete core of the task, "
    "eg create a component, display a list, filter, refactor, setup a project etc (min 40-60 words), start with 'The task involves'"
)

FINAL_ESTIMATION_COMMENT_PROMPT_TEMPLATE = lambda estimate, similars: (
    f"La stima della user story corrente è {estimate}. "
    f"Questi sono gli story point trovati tra i task simili confermati: {similars}.\n\n"
    "In base a questi dati, scrivi una breve frase conclusiva (max 2 frasi) "
    "che indichi coerenza/incoerenza della stima. "
    "Se differisce molto, suggerisci di migliorare la descrizione. "
    "Rispondi in italiano."
)
