
IMAGE_DESCRIPTION_PROMPT = (
    "In massimo due frasi. Indica funzionalità, azioni, input o opzioni presenti. "
    "Evita dettagli grafici, colori o layout puramente visivi."
)

TASK_SIMILARITY_PROMPT_TEMPLATE = lambda target_text, candidate_text: (
    "Confronta tecnicamente due task Jira ignorando completamente dominio, contesto specifico e posizione UI. "
    "Valuta SOLO il livello tecnico dell’attività e la reale complessità implementativa.\n\n"
    "Rispondi `true` esclusivamente se i due task condividono:\n"
    "- Stessa tipologia tecnica (es. entrambi sono liste articolate, entrambi form complessi, "
    "entrambi integrazioni API, entrambi setup o refactor significativi).\n"
    "- Complessità simile (numero di elementi da gestire, presenza di interazioni utente, "
    "livello di struttura dati coinvolta).\n"
    "- Impegno operativo equivalente.\n\n"
    "Se uno dei due è significativamente più semplice, come un form in sola lettura già fatto, "
    "mentre l’altro implica strutture articolate o interazioni più complesse, rispondi sempre `false`.\n\n"
    f"---\nPRIMO TASK:\n{target_text}\n\n"
    f"---\nSECONDO TASK:\n{candidate_text}\n\n"
    "Rispondi solo con `true` o `false`, minuscolo, senza spiegazioni."
)

STORY_POINT_PROMPT = (
    "Sei un assistente agile. Dato il testo di una user story, restituisci lo story point corretto "
    "in scala di Fibonacci ovvero compreso in questa lista [0.5, 1, 2, 3, 5, 8, 13, 21]"
)

ABSTRACT_SUMMARY_PROMPT = (
    "make a synthetic and abstract summary of what needs to be implemented in the task "
    "but without talking about the specific domain at all, you have to extract only the complete core of the task, "
    "eg create a component, display a list, filter, refactor, setup a project etc (min 100 words), start with 'The task involves'"
)

FINAL_ESTIMATION_COMMENT_PROMPT_TEMPLATE = lambda estimate, similars: (
    f"La stima della user story corrente è {estimate}. "
    f"Questi sono gli story point trovati tra i task simili confermati: {similars}.\n\n"
    "In base a questi dati, scrivi una breve frase conclusiva (max 2 frasi) "
    "che indichi coerenza/incoerenza della stima. "
    "Se differisce molto, suggerisci di migliorare la descrizione. "
    "Rispondi in italiano."
)
