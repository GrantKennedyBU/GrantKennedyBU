"""Excerpt: the AI assistant bot's model failover between Claude and OpenAI.

From the bot's private repository (its shared AI client module), shared
here as a sample. Every AI feature in the bot builds two requests, one for each
provider. ask_with_fallback() asks the first and, only if that call fails
after the SDK's own retries (an outage, an overload, a rate limit, a
time-out or a refused request), asks the other provider's model the same
thing. A model that declines to answer counts as an answer, not a failure.

ask_claude(), ask_openai() and the text helpers live in the same module and
are left out here: they hold one shared client per provider and log the
purpose, model, tokens and time of every call, but never its prompt or reply.
"""

# ---------------------------------------------------------------------------
# One model, then the other company's when it fails.
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ClaudeRequest:
    """One Claude call, as ask_claude takes it: the model, the messages, max_tokens, the system prompt and the rest.

    settings: every other request setting (thinking, output_config, timeout,
    ...), passed on unchanged. max_retries: as for ask_claude.
    """
    model: str
    messages: List[Mapping[str, Any]]
    max_tokens: int
    system: Optional[System] = None
    settings: Mapping[str, Any] = field(default_factory=dict)
    max_retries: Optional[int] = None


@dataclass(frozen=True)
class OpenAIRequest:
    """One OpenAI call, as ask_openai takes it: the model, the request (instructions, input, reasoning, ...) and max_retries."""
    model: str
    settings: Mapping[str, Any] = field(default_factory=dict)
    max_retries: Optional[int] = None


Request = Union[ClaudeRequest, OpenAIRequest]


@dataclass(frozen=True)
class Answer:
    """A model's answer, whichever company gave it.

    model: the model that answered. texts: its non-empty text blocks, in
    order (an OpenAI answer has at most one). response: the SDK's answer as
    it came back, for a caller that needs more than the text.
    """
    model: str
    texts: Tuple[str, ...]
    response: Any

    @property
    def text(self) -> str:
        """The answer's text: its text blocks joined by new lines, without surrounding spaces; "" if none."""
        return "\n".join(self.texts).strip()

    @property
    def paused(self) -> bool:
        """True for a Claude answer whose server-side tools (web search) took more steps than one call runs.

        Claude then stops with "pause_turn"; sending the answer's content back
        as the assistant's turn lets it carry on where it stopped.
        """
        return get_field(self.response, "stop_reason") == "pause_turn"

    @property
    def cut_off(self) -> bool:
        """True if the answer stopped at its token ceiling: Claude's "max_tokens", OpenAI's "max_output_tokens"."""
        if get_field(self.response, "stop_reason") == "max_tokens":
            return True
        details = get_field(self.response, "incomplete_details")
        return details is not None and get_field(details, "reason") == "max_output_tokens"


async def ask_with_fallback(purpose: str, first: Request, fallback: Request, *, member: Any = None) -> Answer:
    """Ask `first`; only if that call fails, ask `fallback` (the other company's model) the same thing.

    purpose and member: as for ask_claude; both calls log under the same
    purpose, each with its own model. A failure is any API error the SDK
    raises after its retries (anthropic.APIError, openai.APIError): a
    connection error, a time-out, a rate limit, an overload, a server error
    or a refused request. The first model's failure is logged as a warning,
    or as an error (an alert) when it is lasting (LASTING_FAILURE_STATUSES),
    since that one won't fix itself. Anything else, such as a bug in a
    request, is raised at once without trying the fallback.

    Returns the Answer of whichever model answered. Raises the fallback's
    error when both calls fail, with the first one's as its cause.
    """
    try:
        return await _ask(purpose, first, member)
    except (anthropic.APIError, openai.APIError) as first_error:
        _log_fallback(purpose, first, fallback, first_error)
        try:
            return await _ask(purpose, fallback, member)
        except Exception as fallback_error:
            # The caller logs one traceback that shows both failures.
            raise fallback_error from first_error


async def _ask(purpose: str, request: Request, member: Any) -> Answer:
    """Make one call from a ClaudeRequest or an OpenAIRequest and wrap its answer."""
    # max_retries goes along only when the request sets it.
    retries = {} if request.max_retries is None else {"max_retries": request.max_retries}
    if isinstance(request, ClaudeRequest):
        response = await ask_claude(purpose, model=request.model, messages=request.messages,
                                    max_tokens=request.max_tokens, system=request.system, member=member,
                                    **retries, **request.settings)
        return Answer(request.model, tuple(claude_text_blocks(response)), response)
    response = await ask_openai(purpose, model=request.model, member=member, **retries, **request.settings)
    text = openai_text(response)
    return Answer(request.model, (text,) if text else (), response)


def _log_fallback(purpose: str, failed: Request, fallback: Request, error: Exception) -> None:
    """Log that `failed` gave no answer and `fallback` is asked instead: an error if it won't fix itself.

    The error itself goes in the log file (its message holds the API's
    reason, such as "model not found"); alerts leave tracebacks out.
    """
    status = getattr(error, "status_code", None)
    lasting = status in LASTING_FAILURE_STATUSES
    reason = f"was refused (HTTP {status})" if lasting else f"failed ({type(error).__name__})"
    log.log(logging.ERROR if lasting else logging.WARNING,
            "The %s %s call %s; asking %s instead", failed.model, purpose, reason, fallback.model,
            exc_info=error, extra=event("ai.fallback", purpose=purpose, model=failed.model, fallback=fallback.model,
                        status=status))

