using NUnit.Framework;

public sealed class SessionConnectionTests
{
    [TestCase("abcd1234", "ABCD-1234")]
    [TestCase("ABCD-1234", "ABCD-1234")]
    [TestCase(" abcd-1234 ", "ABCD-1234")]
    public void NormalizeSessionCodeFormatsInput(string input, string expected)
    {
        Assert.AreEqual(expected, SessionConnection.NormalizeSessionCode(input));
    }

    [TestCase("ABCD-1234", true)]
    [TestCase("ABC", false)]
    [TestCase("ABCI-1234", false)]
    [TestCase("ABCD-123!", false)]
    public void SessionCodeValidationUsesCrockfordAlphabet(string input, bool expected)
    {
        Assert.AreEqual(expected, SessionConnection.IsValidSessionCode(input));
    }

    [Test]
    public void ApiErrorsHaveFriendlyMessages()
    {
        StringAssert.Contains("wygasł", SessionConnection.FriendlyError("invalid_or_expired_code"));
        StringAssert.Contains("inną aplikacją", SessionConnection.FriendlyError("role_already_paired"));
    }
}
