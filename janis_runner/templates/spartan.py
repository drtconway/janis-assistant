from typing import Union, List

from janis_runner.engines.enginetypes import EngineType
from janis_runner.engines.cromwell.cromwellconfiguration import CromwellConfiguration
from janis_runner.templates.base import EnvironmentTemplate


class SpartanTemplate(EnvironmentTemplate):

    # default_recipes = {
    #     "hg38": {
    #         "reference": "/data/projects/punim0755/hg38/assembly_contigs_renamed/Homo_sapiens_assembly38.fasta",
    #         "snps_dbsnp": "/data/cephfs/punim0755/hg38/dbsnp_contigs_renamed/Homo_sapiens_assembly38.dbsnp138.vcf.gz",
    #         "snps_1000gp": "/data/cephfs/punim0755/hg38/snps_1000GP/1000G_phase1.snps.high_confidence.hg38.vcf.gz",
    #         "known_indels": "/data/cephfs/punim0755/hg38/known_indels_contigs_renamed/Homo_sapiens_assembly38.known_indels.vcf.gz",
    #         "mills_1000gp_indels": "/data/cephfs/punim0755/hg38/mills_indels/Mills_and_1000G_gold_standard.indels.hg38.vcf.gz",
    #     }
    # }

    def __init__(
        self,
        executionDir,
        queues: Union[str, List[str]] = "physical",
        email=None,
        containerDir="/config/binaries/singularity/containers_devel/janis/",
        singularityVersion="3.2.0-spartan_gcc-6.2.0",
    ):

        super().__init__()
        self.execution_dir = executionDir
        self.queues = queues
        self.email = email
        self.container_dir = containerDir
        self.singularity_version = singularityVersion

    def cromwell(self):
        queues = self.queues
        if not isinstance(self.queues, list):
            queues = [self.queues]

        config = CromwellConfiguration(
            backend=CromwellConfiguration.Backend(
                default="slurm-spartan",
                providers={
                    "slurm-spartan": CromwellConfiguration.Backend.Provider.slurm_singularity(
                        singularityloadinstructions=f"module load Singularity/{self.singularity_version}",
                        singularitycontainerdir=self.container_dir,
                        buildinstructions=(
                            f"singularity pull $image docker://${{docker}}"
                        ),
                        jobemail=self.email,
                        jobqueues=queues,
                    )
                },
            )
        )

        backend: CromwellConfiguration.Backend.Provider.Config = config.backend.providers[
            config.backend.default
        ].config
        backend.root = self.execution_dir
        backend.filesystems = {
            "local": {
                "localization": ["cached-copy", "hard-link", "soft-link", "copy"]
            },
            # "caching": {"hashing-strategy": "path+modtime"},
        }

        return config

    def engine_config(self, engine: EngineType):
        if engine == EngineType.cromwell:
            return self.cromwell()

        raise NotImplementedError(
            f"The {self.__class__.__name__} template does not have a configuration for {engine.value}"
        )
