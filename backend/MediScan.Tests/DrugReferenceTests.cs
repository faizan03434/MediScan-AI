using MediScan.Infra.External;

namespace MediScan.Tests;

public class DrugReferenceTests
{
    private const string Label = """
        {"results":[{"set_id":"test-label-id","openfda":{"brand_name":["Another Brand","Exact Brand"],"generic_name":["acetaminophen"]},"warnings":["Ask a doctor before use."],"drug_interactions":["Read label for interactions."]}]}
        """;

    [Fact]
    public void RejectsPartialAndUnrelatedNames()
    {
        Assert.Null(DrugDataService.ParseOpenFdaLabel(Label, "OpenFDA", "Brand"));
        Assert.Null(DrugDataService.ParseOpenFdaLabel(Label, "OpenFDA", "Amoxicillin"));
    }
    [Fact]
    public void ExactAliasKeepsIdentityAndDoesNotVerifyPrescription()
    {
        var result = DrugDataService.ParseOpenFdaLabel(Label, "OpenFDA exact name", "Exact Brand");
        Assert.NotNull(result);
        Assert.Equal("Exact Brand", result.BrandName);
        Assert.False(result.PrescriptionVerified);
        Assert.Contains("test-label-id", result.ReferenceUrl);
        Assert.Contains(result.Warnings, w => w.Contains("Pakistan registration"));
    }
}
