from setuptools import setup, find_packages

setup(
    name='shotgun_api3_registry',
    version='1.0',
    description='API keys and config for Western Post\'s Shotgun instances.',
    
    packages=find_packages(exclude=['build*', 'tests*']),
    include_package_data=True,
    
    author='Mike Boers',
    author_email='shotgun_api3_registry@mikeboers.com',
    license='all rights reserved',
    
    entry_points={
        # For the primary runtime.
        'sgschema_cache': [
            '000_shotgun_api3_registry = shotgun_api3_registry.schema:load_cached',
        ],
        # For caching the above.
        'sgschema_loaders': [
            '050_shotgun_api3_registry = shotgun_api3_registry.schema:load',
        ],
    },
    
)