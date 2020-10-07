from aries_cloudagent.config.injection_context import InjectionContext


async def setup(context: InjectionContext):
    registry = context.settings.get("public_storage_registered_types")
    registry.update(
        {"thcf_data_vault": "thcf_data_vault_driver.v1_0.data_vault.THCFDataVault"}
    )
