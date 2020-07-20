PROTOCOL_URI = "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/verifiable-services/1.0"
PROTOCOL_PACKAGE_DISCOVERY = "services.discovery"

DISCOVERY = f"{PROTOCOL_URI}/discovery"
DISCOVERY_RESPONSE = f"{PROTOCOL_URI}/discovery-response"

MESSAGE_TYPES = {
    DISCOVERY: f"{PROTOCOL_PACKAGE_DISCOVERY}.Discovery",
    DISCOVERY_RESPONSE: f"{PROTOCOL_PACKAGE_DISCOVERY}.DiscoveryResponse",
}
