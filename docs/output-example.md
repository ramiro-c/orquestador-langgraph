# Research

## Consulta

Dame un analisis de Grok bot vs Hermes agent bot

## research_notes

Aquí tienes un brief con los hechos sobre Grok Bot y Hermes Agent:

### Hallazgos:

*   **Grok Bot:**
    *   Ofrece una fuerza de trabajo de IA gestionada con acceso inmediato al navegador.
    *   Utiliza una computadora en la nube propietaria de xAI.
    *   Se comercializa como un "empleado de IA terminado".
    *   Presenta una barrera de entrada más baja y una configuración más sencilla, funcionando "directamente de la caja".
    *   Todos los bots comparten una única computadora asociada a la cuenta, incluyendo archivos, sesiones de navegador e inicios de sesión de aplicaciones.
    *   Las habilidades se pueden grabar demostrando un flujo de trabajo (hasta 10 minutos).
    *   Es propietario, lo que significa que los usuarios están vinculados al proveedor de modelos de Grok.
    *   Su enfoque es tener un "equipo completo de diferentes personas" realizando el trabajo.
*   **Hermes Agent:**
    *   Ofrece agentes de IA de código abierto y personalizables.
    *   Tiene licencia MIT.
    *   Requiere más configuración y ajustes, lo que implica una barrera de entrada más alta para usuarios no técnicos.
    *   Proporciona las "piezas para construir uno" en lugar de un producto terminado.
    *   Los usuarios lo ejecutan ellos mismos (autoalojado en una computadora portátil, VPS o contenedor).
    *   Aísla a los agentes; la memoria reside en archivos planos.
    *   Mantiene el perfil de credenciales limitado al host que ejecuta Hermes.
    *   Un bot es un perfil de Hermes Agent que contiene configuración, claves, un archivo SOUL, memoria, sesiones, habilidades y estado de cron.
    *   Los agentes pueden escribir sus propias habilidades, y un curador en segundo plano elimina las que no se utilizan.
*   **Similitudes:**
    *   Ambos ofrecen memoria persistente, tareas programadas, acceso a herramientas y ejecución de múltiples pasos.
    *   Ambos buscan proporcionar trabajadores de IA "siempre activos".
    *   La principal diferencia radica en la arquitectura: quién posee la máquina, quién ve lo que hace el agente y el control del proveedor.

### Citas Cortas:

*   "Grok Bot sells you a finished AI employee. Hermes sells you the parts to build one and keeps the receipts." - Towards AI
*   "Grok Bot takes the opposite approach, with every Bot sharing one account-scoped computer. That includes files, browser sessions, and app logins, and xAI says those survive the deletion of the Bot that created them." - The New Stack
*   "Hermes is the easiest to read because its code is open." - The New Stack
*   "Grok Bot just works out of the box. There's no crazy setup needed. There's no crashing. Right, that is really the challenge with Hermes and Openclaw is there's tons of setup and tinkering need to be done. And if you're not super technical, it becomes challenging and it will crash a lot." - YouTube (Did Grok Bot just kill Hermes and OpenClaw?)

### Fuentes:

*   **Grok Bot vs Hermes Agent (Which one is Better?)**
    *   https://www.youtube.com/watch?v=t7aBvFxOwUg
*   **Grok Bot vs Hermes Agent: Which “Always-On” AI Worker Should You Trust?**
    *   https://pub.towardsai.net/grok-bot-vs-hermes-agent-which-always-on-ai-worker-should-you-trust-eb6d48f056ec
*   **Grok, Claude, and Hermes agents get job titles**
    *   https://thenewstack.io/persistent-ai-agent-identities
*   **OpenClaw vs. Hermes vs. Grok @bot, clearly explained: All ...**
    *   https://x.com/_avichawla/status/2090368200693440841
*   **Did Grok Bot just kill Hermes and OpenClaw?**
    *   https://www.youtube.com/watch?v=lc6hKU4BdsA

## analysis

El sentimiento general de las notas de investigación es **positivo** con un score de 0.269.

**Evidencias:**

*   **Positivo:** Grok Bot es elogiado por su facilidad de uso y configuración ("Grok Bot just works out of the box. There's no crazy setup needed. There's no crashing."), mientras que Hermes Agent es valorado por ser de código abierto y personalizable ("Ofrece agentes de IA de código abierto y personalizables" y "Hermes is the easiest to read because its code is open.").
*   **Negativo:** Se señalan preocupaciones sobre la privacidad y seguridad de Grok Bot ("Todos los bots comparten una única computadora asociada a la cuenta, incluyendo archivos, sesiones de navegador e inicios de sesión de aplicaciones" y "Grok Bot takes the opposite approach, with every Bot sharing one account-scoped computer. That includes files, browser sessions, and app logins, and xAI says those survive the deletion of the Bot that created them."). Para Hermes Agent, la dificultad de configuración es un punto negativo ("Requiere más configuración y ajustes, lo que implica una barrera de entrada más alta para usuarios no técnicos" y "Right, that is really the challenge with Hermes and Openclaw is there's tons of setup and tinkering need to be done. And if you're not super technical, it becomes challenging and it will crash a lot.").
*   **Neutral:** Algunas descripciones son puramente informativas, como que Grok Bot "Utiliza una computadora en la nube propietaria de xAI" o que Hermes Agent "Proporciona las 'piezas para construir uno' en lugar de un producto terminado".
