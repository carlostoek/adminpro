# Phase 13: VIP Ritualized Entry Flow - Context

**Gathered:** 2026-01-27
**Status:** Ready for planning

<domain>
## Phase Boundary

Replace the current VIP access flow (immediate link delivery) with a 3-phase sequential admission process that increases exclusivity perception, reduces impulsive access, and psychologically prepares users for the content type. The link is only delivered after completing all 3 stages.

**Entry condition:** User has valid VIPSubscriber record with `vip_entry_stage=1` (triggered by activation link)

**Exit condition:** User completes Stage 3, receives 24-hour invite link, joins channel, and is assigned UserRole.VIP

</domain>

<decisions>
## Implementation Decisions

### Ritual tone & progression
- **Continuous flow:** Messages reference each other as one extended conversation broken into steps
- **Stage-specific button progression:** Stage 1 = "Continuar", Stage 2 = "Estoy listo", Stage 3 = embedded link button
- **Consistent visual identity:** Always use 🎩 emoji for Lucien (not stage-specific emojis)
- **One definitive message per stage:** No variations. Every VIP gets the same ritual experience.
- **Direct delivery in Stage 3:** No explicit acknowledgment of "Estoy listo" commitment — the button click IS the acknowledgment

### Message progression (from design spec)
- **Stage 1 (Activation):** Mysterious acknowledgment emphasizing exclusivity. "Veo que ha dado el paso que muchos contemplan... y pocos toman."
- **Stage 2 (Expectations):** Intimate warning about the nature of the space. "El Diván no es un lugar donde se mira y se olvida. Es un espacio íntimo, sin filtros..."
- **Stage 3 (Delivery):** Dramatic delivery with link. "Entonces no le haré esperar más. Diana le abre la puerta al Diván."

### Abandonment & resumption
- **Seamless resumption:** When user returns, continue from current stage as if no time passed. No acknowledgment of time gap.
- **No abandonment limit:** User can leave and return indefinitely. The door remains open as long as VIPSubscriber is valid.
- **State persists:** `vip_entry_stage` field tracks progress (1 → 2 → 3 → complete). Resume based on this value.

### Expiry & cancellation
- **Expiry blocks continuation:** If VIPSubscriber expires during Stages 1-2, show Lucien-voiced expiry message and block further progress. No retry option.
- **Expiry uses Lucien's voice:** Consistent with ritual tone. Not a neutral system message.
- **Immediate removal on expiry:** If VIPSubscriber expires within the 24-hour link window, user is removed from VIP channel and link becomes invalid immediately.

### Link delivery experience
- **Abstract expiry time:** Show "24 hours" not timestamp. "Tiene 24 horas para usar el enlace." Keep mysterious, not anxious.
- **Dramatic button text:** Link button says "Cruzar el umbral" — fits the ritual/gatekeeper theme.
- **No channel welcome message:** Stage 3 delivery IS the welcome. No duplicate automated message when they join the channel.
- **Link validity:** 24 hours from generation. One-time use. Becomes invalid if VIPSubscriber expires.

### Claude's Discretion
- Exact wording of expiry message (as long as it uses Lucien's voice and blocks continuation)
- Technical implementation of stage transition (FSM states vs. direct field updates)
- Background task timing for expiry checks (already have expire_vip_subscribers task)

</decisions>

<specifics>
## Specific Ideas

**Complete message design from user's spec:**

**Stage 1:**
> 🎩 Lucien:
>
> Veo que ha dado el paso que muchos contemplan… y pocos toman.
>
> Su acceso al Diván de Diana está siendo preparado.
>
> Este no es un espacio público.
> No es un canal más.
> Y definitivamente no es para quien solo siente curiosidad.
>
> Antes de entregarle la entrada, hay algo que debe saber…
>
> [Continuar]

**Stage 2:**
> 🎩 Lucien:
>
> El Diván no es un lugar donde se mira y se olvida.
> Es un espacio íntimo, sin filtros, sin máscaras.
>
> Aquí Diana se muestra sin la distancia de las redes,
> y eso exige discreción, respeto y presencia real.
>
> Si ha llegado hasta aquí solo para observar de paso…
> este es el momento de detenerse.
>
> Si entiende lo que significa entrar… entonces sí.
>
> [Estoy listo]

**Stage 3:**
> 🎩 Lucien:
>
> Entonces no le haré esperar más.
>
> Diana le abre la puerta al Diván.
>
> Este acceso es personal.
> No se comparte.
> No se replica.
> Y se cierra cuando el vínculo termina.
>
> Tiene 24 horas para usar el enlace.
>
> Entre con intención.
>
> 👇
>
> [Cruzar el umbral] → VIP invite link button

**Key vocabulary:** "Diván de Diana", "umbral", "círculo", "presencia real", "sin máscaras"

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 13-vip-ritualized-entry*
*Context gathered: 2026-01-27*
