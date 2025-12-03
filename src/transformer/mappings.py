"""
React to Angular mappings and transformations.
"""

from typing import Dict, Any


class ReactAngularMappings:
    """Mappings between React and Angular concepts."""

    # Component lifecycle mappings
    LIFECYCLE_MAPPINGS = {
        "componentDidMount": "ngOnInit",
        "componentDidUpdate": "ngAfterViewChecked",
        "componentWillUnmount": "ngOnDestroy",
        "componentDidCatch": "ngOnError",
    }

    # Hook mappings
    HOOK_MAPPINGS = {
        "useState": "property",
        "useEffect": "ngOnInit/ngOnDestroy",
        "useContext": "inject",
        "useRef": "ViewChild/ElementRef",
        "useMemo": "getter",
        "useCallback": "method",
    }

    # Event handler mappings
    EVENT_MAPPINGS = {
        "onClick": "click",
        "onChange": "change",
        "onSubmit": "submit",
        "onFocus": "focus",
        "onBlur": "blur",
        "onKeyDown": "keydown",
        "onKeyUp": "keyup",
        "onMouseEnter": "mouseenter",
        "onMouseLeave": "mouseleave",
    }

    # JSX to Angular template mappings
    JSX_MAPPINGS = {
        "className": "class",
        "htmlFor": "for",
    }

    def get_lifecycle_mapping(self, react_lifecycle: str) -> str:
        """Get Angular equivalent for React lifecycle method."""
        return self.LIFECYCLE_MAPPINGS.get(react_lifecycle, "")

    def get_hook_mapping(self, react_hook: str) -> str:
        """Get Angular equivalent for React hook."""
        return self.HOOK_MAPPINGS.get(react_hook, "")

    def get_event_mapping(self, react_event: str) -> str:
        """Get Angular equivalent for React event handler."""
        return self.EVENT_MAPPINGS.get(react_event, react_event.lower())

    def get_jsx_attr_mapping(self, jsx_attr: str) -> str:
        """Get Angular equivalent for JSX attribute."""
        return self.JSX_MAPPINGS.get(jsx_attr, jsx_attr.lower())

