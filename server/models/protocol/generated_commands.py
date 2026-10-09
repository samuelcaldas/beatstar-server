# Auto-generated Pydantic Models from Beatstar IL2CPP Protocol
from __future__ import annotations
from typing import Any, Optional, list as ListType
from pydantic import BaseModel, Field


class AdTotaliserExpired_SharplaAudit(BaseModel):
    """Category: audit_event. Base: SharplaCmdAudit"""

    pass


class AddFriend_Req(BaseModel):
    """Category: request. Base: RakshaItem"""

    clide: Optional[str] = None
    socialSource: Optional[str] = None


class AddFriend_Resp(BaseModel):
    """Category: response. Base: RakshaItem"""

    result: Optional[Any] = None


class AddRooster_SharplaAudit(BaseModel):
    """Category: audit_event. Base: SharplaCmdAudit"""

    query: Optional[str] = None
    openEnded: Optional[bool] = None


class AnswerQuestionnaire_SharplaAudit(BaseModel):
    """Category: audit_event. Base: SharplaCmdAudit"""

    questionnaire_id: Optional[int] = None
    answers: Optional[ListType[Any]] = None


class BatchRequestHeader(BaseModel):
    """Category: header. Base: RakshaItem"""

    clide: Optional[str] = None
    lastResponseTimestampMsecs: Optional[int] = None
    preventProfileWrites: Optional[bool] = None
    profileVersion: Optional[int] = None


class BatchResponseHeader(BaseModel):
    """Category: header. Base: RakshaItem"""

    pass


class BuyAttemptForLeaderboardEvent_SharplaAudit(BaseModel):
    """Category: audit_event. Base: SharplaCmdAudit"""

    game_id: Optional[int] = None


class BuyLeaderboardEventBundleBox_SharplaAudit(BaseModel):
    """Category: audit_event. Base: SharplaCmdAudit"""

    eventTemplate_id: Optional[int] = None
    optionalIntendedBeatmap_id: Optional[int] = None


class BuyShopItem_SharplaAudit(BaseModel):
    """Category: audit_event. Base: SharplaCmdAudit"""

    ToBuy_id: Optional[int] = None
    IAPPurchasesProduct: Optional[Any] = None
    RewardSource: Optional[Any] = None


class BuyShopThemedBox_SharplaAudit(BaseModel):
    """Category: audit_event. Base: SharplaCmdAudit"""

    themeBox_id: Optional[int] = None


class BuySongForLeaderboardEvent_SharplaAudit(BaseModel):
    """Category: audit_event. Base: SharplaCmdAudit"""

    beatmap_id: Optional[int] = None


class BuyTicketForLeaderboardEvent_SharplaAudit(BaseModel):
    """Category: audit_event. Base: SharplaCmdAudit"""

    game_id: Optional[int] = None
    spinCount: Optional[int] = None


class Cheat_SharplaAudit(BaseModel):
    """Category: audit_event. Base: SharplaCmdAudit"""

    cheat: Optional[Any] = None
    value1: Optional[int] = None
    string1: Optional[str] = None
    value2: Optional[int] = None
    longvalue1: Optional[int] = None
    dontMarkTransactionsAsSeen: Optional[bool] = None


class ChooseBeatmapOption_SharplaAudit(BaseModel):
    """Category: audit_event. Base: SharplaCmdAudit"""

    transactionId: Optional[int] = None
    beatmapId: Optional[int] = None


class ClaimAppleMusicSignup_SharplaAudit(BaseModel):
    """Category: audit_event. Base: SharplaCmdAudit"""

    matchedBeatmaps_id: Optional[ListType[int]] = None


class ClaimCards_SharplaAudit(BaseModel):
    """Category: audit_event. Base: SharplaCmdAudit"""

    transactionId: Optional[int] = None
    claimOption: Optional[int] = None
    caseOption_id: Optional[int] = None


class ClaimClaimableReward_SharplaRpcReq(BaseModel):
    """Category: request. Base: SharplaRpcRequest"""

    pass


class ClaimClaimableReward_SharplaRpcResp(BaseModel):
    """Category: response. Base: SharplaRpcResponse"""

    rewards: Optional[ListType[Any]] = None


class ClaimCosmeticRemovalReward_SharplaAudit(BaseModel):
    """Category: audit_event. Base: SharplaCmdAudit"""

    cosmeticId: Optional[int] = None
    cosmeticType: Optional[Any] = None


class ClaimFreeSongChoicePromo_SharplaAudit(BaseModel):
    """Category: audit_event. Base: SharplaCmdAudit"""

    template_id: Optional[int] = None
    beatmapChoice_id: Optional[int] = None


class ClaimIAP_SharplaAudit(BaseModel):
    """Category: audit_event. Base: SharplaCmdAudit"""

    IAPTemplate_id: Optional[str] = None
    PurchasesProduct: Optional[Any] = None


class ClaimLeaderboardEventReward_SharplaAudit(BaseModel):
    """Category: audit_event. Base: SharplaCmdAudit"""

    game_id: Optional[int] = None


class ClaimReactivationBundle_SharplaAudit(BaseModel):
    """Category: audit_event. Base: SharplaCmdAudit"""

    reactivationBundle_id: Optional[int] = None
    debugAllow: Optional[bool] = None


class ClaimSongRemovalReward_SharplaAudit(BaseModel):
    """Category: audit_event. Base: SharplaCmdAudit"""

    forBeatmapRemovedId: Optional[int] = None


class ClaimSongsDisabledReward_SharplaAudit(BaseModel):
    """Category: audit_event. Base: SharplaCmdAudit"""

    disabledBeatmapIds: Optional[ListType[int]] = None


class ClaimStarMilestone_SharplaAudit(BaseModel):
    """Category: audit_event. Base: SharplaCmdAudit"""

    milestone_id: Optional[int] = None


class ClaimVideoAdRewardsOnRestart_SharplaAudit(BaseModel):
    """Category: audit_event. Base: SharplaCmdAudit"""

    pass


class ClaimableReward(BaseModel):
    """Category: data_model. Base: RakshaItem"""

    id: Optional[str] = None
    message: Optional[str] = None
    rewards: Optional[ListType[Any]] = None
    source: Optional[Any] = None


class ClearIAPPurchase_SharplaAudit(BaseModel):
    """Category: audit_event. Base: SharplaCmdAudit"""

    iapPurchaseData: Optional[Any] = None


class ClearShopIAPState_SharplaAudit(BaseModel):
    """Category: audit_event. Base: SharplaCmdAudit"""

    ForShopItem_id: Optional[int] = None


class CompleteIAPPurchase_SharplaAudit(BaseModel):
    """Category: audit_event. Base: SharplaCmdAudit"""

    purchasedProduct: Optional[Any] = None
    purchaseData: Optional[Any] = None


class ContinueRhythmGame_SharplaAudit(BaseModel):
    """Category: audit_event. Base: SharplaCmdAudit"""

    starIndex: Optional[int] = None
    retryCount: Optional[int] = None


class ContinueWithWishlistBoxOpen_SharplaAudit(BaseModel):
    """Category: audit_event. Base: SharplaCmdAudit"""

    likeSongsToOpenWishlistTransactionStep: Optional[Any] = None


class DebugOnlyGetPlayerProfile_Req(BaseModel):
    """Category: request. Base: RakshaItem"""

    clide: Optional[str] = None


class DebugOnlyGetPlayerProfile_Resp(BaseModel):
    """Category: response. Base: RakshaItem"""

    player: Optional[Any] = None
    regularLeaderboardPercentile: Optional[int] = None
    deluxeLeaderboardPercentile: Optional[int] = None


class DeluxeInteractionScoringAnalytics(BaseModel):
    """Category: data_model. Base: RakshaItem"""

    diagonalSwipesScore: Optional[int] = None
    diagonalSwipesPossibleScore: Optional[int] = None
    switchHoldsStartScore: Optional[int] = None
    switchHoldsPossibleStartScore: Optional[int] = None
    switchHoldsIntermediateBeatsScore: Optional[int] = None
    switchHoldsPossibleIntermediateBeatsScore: Optional[int] = None
    switchHoldSwipesFlickScore: Optional[int] = None
    switchHoldSwipesPossibleFlickScore: Optional[int] = None


class EmptyReq(BaseModel):
    """Category: data_model. Base: RakshaItem"""

    pass


class EmptyResp(BaseModel):
    """Category: data_model. Base: RakshaItem"""

    pass


class EndAdWatch_SharplaAudit(BaseModel):
    """Category: audit_event. Base: SharplaCmdAudit"""

    adWasRewarded: Optional[bool] = None


class EndShowdown_SharplaRpcReq(BaseModel):
    """Category: request. Base: SharplaRpcRequest"""

    game_id: Optional[int] = None


class EndShowdown_SharplaRpcResp(BaseModel):
    """Category: response. Base: SharplaRpcResponse"""

    playerPosition: Optional[int] = None
    showdownTO: Optional[Any] = None


class ExpireBonusCardsSystem_SharplaAudit(BaseModel):
    """Category: audit_event. Base: SharplaCmdAudit"""

    skipped: Optional[bool] = None


class FriendBragReceived_SharplaAudit(BaseModel):
    """Category: audit_event. Base: SharplaCmdAudit"""

    Brag: Optional[Any] = None


class FriendBragSent_SharplaAudit(BaseModel):
    """Category: audit_event. Base: SharplaCmdAudit"""

    targetPlayerId: Optional[str] = None
    beatmap_id: Optional[int] = None


class FriendLeaderboardSynced_SharplaAudit(BaseModel):
    """Category: audit_event. Base: SharplaCmdAudit"""

    beatmap_id: Optional[int] = None
    entries: Optional[ListType[Any]] = None


class FriendViews_Req(BaseModel):
    """Category: request. Base: RakshaItem"""

    clides: Optional[ListType[str]] = None


class FriendViews_Resp(BaseModel):
    """Category: response. Base: RakshaItem"""

    views: Optional[ListType[Any]] = None
    invalidClides: Optional[ListType[str]] = None


class Friends_Req(BaseModel):
    """Category: request. Base: RakshaItem"""

    pass


class Friends_Resp(BaseModel):
    """Category: response. Base: RakshaItem"""

    friends: Optional[ListType[str]] = None
    incomingFriends: Optional[ListType[str]] = None
    desiredFriends: Optional[ListType[str]] = None
    errorCode: Optional[int] = None


class GenerateBonusCardsRewardInProgress_SharplaAudit(BaseModel):
    """Category: audit_event. Base: SharplaCmdAudit"""

    pass


class GetCurrentUserProfile_Req(BaseModel):
    """Category: request. Base: RakshaItem"""

    pass


class GetCurrentUserProfile_Resp(BaseModel):
    """Category: response. Base: RakshaItem"""

    profile: Optional[Any] = None


class GetGooglePlayGroupingPersona_Req(BaseModel):
    """Category: request. Base: RakshaItem"""

    pass


class GetGooglePlayGroupingPersona_Resp(BaseModel):
    """Category: response. Base: RakshaItem"""

    persona: Optional[str] = None


class GetMusicKitAuthentication_Req(BaseModel):
    """Category: request. Base: RakshaItem"""

    pass


class GetMusicKitAuthentication_Resp(BaseModel):
    """Category: response. Base: RakshaItem"""

    token: Optional[str] = None
    dateMsecs: Optional[int] = None


class GetMusicKitDeveloperToken_Req(BaseModel):
    """Category: request. Base: RakshaItem"""

    bundleId: Optional[str] = None


class GetMusicKitDeveloperToken_Resp(BaseModel):
    """Category: response. Base: RakshaItem"""

    developerToken: Optional[str] = None
    expiryMsecs: Optional[int] = None


class GetNameUidLegacy_Req(BaseModel):
    """Category: request. Base: RakshaItem"""

    pass


class GetNameUidLegacy_Resp(BaseModel):
    """Category: response. Base: RakshaItem"""

    nameUid: Optional[int] = None


class GetNameUid_Req(BaseModel):
    """Category: request. Base: RakshaItem"""

    pass


class GetNameUid_Resp(BaseModel):
    """Category: response. Base: RakshaItem"""

    nameUid: Optional[int] = None


class GetPublicProfile_SharplaRpcReq(BaseModel):
    """Category: request. Base: SharplaRpcRequest"""

    clide: Optional[str] = None


class GetPublicProfile_SharplaRpcResp(BaseModel):
    """Category: response. Base: SharplaRpcResponse"""

    profile: Optional[Any] = None
    leaderboardInfo: Optional[Any] = None
    deluxeLeaderboardInfo: Optional[Any] = None


class HideBrag_SharplaAudit(BaseModel):
    """Category: audit_event. Base: SharplaCmdAudit"""

    bragId: Optional[str] = None


class InteractionTypeAndCountsPerStreakMultiplier(BaseModel):
    """Category: data_model. Base: RakshaItem"""

    InteractionType: Optional[Any] = None
    CountsPerStreakMultiplier: Optional[ListType[int]] = None
    ScoreTypeCounts: Optional[ListType[Any]] = None
    NumOfLateOkScoreTypes: Optional[int] = None


class JoinShowdown_SharplaRpcReq(BaseModel):
    """Category: request. Base: SharplaRpcRequest"""

    game_id: Optional[int] = None
    beatmap_id: Optional[int] = None


class JoinShowdown_SharplaRpcResp(BaseModel):
    """Category: response. Base: SharplaRpcResponse"""

    data: Optional[Any] = None
    beatmaps_id: Optional[ListType[int]] = None


class LeaderboardWithViews_Req(BaseModel):
    """Category: request. Base: RakshaItem"""

    leaderboardName: Optional[str] = None
    friendsOnly: Optional[bool] = None
    startIndex: Optional[int] = None
    count: Optional[int] = None
    supercellIdFriendClides: Optional[ListType[str]] = None


class LeaderboardWithViews_Resp(BaseModel):
    """Category: response. Base: RakshaItem"""

    results: Optional[ListType[Any]] = None
    isError: Optional[bool] = None
    playerLeaderboardInfo: Optional[Any] = None
    nextIndex: Optional[int] = None


class Leaderboard_Req(BaseModel):
    """Category: request. Base: RakshaItem"""

    leaderboardName: Optional[str] = None
    friendsOnly: Optional[bool] = None
    startIndex: Optional[int] = None
    count: Optional[int] = None
    supercellIdFriendClides: Optional[ListType[str]] = None


class Leaderboard_Resp(BaseModel):
    """Category: response. Base: RakshaItem"""

    results: Optional[ListType[Any]] = None
    isError: Optional[bool] = None
    playerLeaderboardInfo: Optional[Any] = None


class LiveOpsDeeplinkClaimLink_SharplaAudit(BaseModel):
    """Category: audit_event. Base: SharplaCmdAudit"""

    liveOpsDeeplinkReward: Optional[Any] = None
    campaignIdForAnalytics: Optional[str] = None


class LiveOpsDeeplinkCollectRewards_SharplaAudit(BaseModel):
    """Category: audit_event. Base: SharplaCmdAudit"""

    liveOpsDeeplinkReward: Optional[Any] = None


class LiveOpsEvent_End_SharplaAudit(BaseModel):
    """Category: audit_event. Base: SharplaCmdAudit"""

    eventToEnd_id: Optional[int] = None


class LiveOpsEvent_Start_SharplaAudit(BaseModel):
    """Category: audit_event. Base: SharplaCmdAudit"""

    eventToStart_id: Optional[int] = None


class LiveOpsTotaliserEvent_BoostSongPoints_SharplaAudit(BaseModel):
    """Category: audit_event. Base: SharplaCmdAudit"""

    game_id: Optional[int] = None
    beatmap_id: Optional[int] = None


class LiveOpsTotaliserEvent_ClaimTotaliserReward_SharplaAudit(BaseModel):
    """Category: audit_event. Base: SharplaCmdAudit"""

    game_id: Optional[int] = None
    rewardIndex: Optional[int] = None


class LiveOpsTotaliserEvent_RefreshBeatmaps_SharplaAudit(BaseModel):
    """Category: audit_event. Base: SharplaCmdAudit"""

    game_id: Optional[int] = None


class LiveOpsTotaliserEvent_SetTrackSkinForGenre_SharplaAudit(BaseModel):
    """Category: audit_event. Base: SharplaCmdAudit"""

    genre_id: Optional[int] = None
    trackSkin_id: Optional[int] = None


class LiveOpsTotaliserEvent_SwapBeatmap_SharplaAudit(BaseModel):
    """Category: audit_event. Base: SharplaCmdAudit"""

    game_id: Optional[int] = None
    beatmap_id: Optional[int] = None


class LogicRpcs(BaseModel):
    """Category: data_model. Base: RakshaDatabase"""

    version: Optional[str] = None


class MakeGameCurrencyPurchase_SharplaAudit(BaseModel):
    """Category: audit_event. Base: SharplaCmdAudit"""

    purchaseData: Optional[Any] = None


class MarkSeenDatedRooster_SharplaAudit(BaseModel):
    """Category: audit_event. Base: SharplaCmdAudit"""

    key: Optional[int] = None
    dateMsecs: Optional[int] = None


class MarkSeenRooster_SharplaAudit(BaseModel):
    """Category: audit_event. Base: SharplaCmdAudit"""

    query: Optional[str] = None
    openEnded: Optional[bool] = None
    queries: Optional[ListType[str]] = None


class MarkSeenStringDatedRooster_SharplaAudit(BaseModel):
    """Category: audit_event. Base: SharplaCmdAudit"""

    key: Optional[str] = None
    dateMsecs: Optional[int] = None


class MarkTransactionSeen_SharplaAudit(BaseModel):
    """Category: audit_event. Base: SharplaCmdAudit"""

    uid: Optional[int] = None


class MarkTransactionStepSeen_SharplaAudit(BaseModel):
    """Category: audit_event. Base: SharplaCmdAudit"""

    uids: Optional[ListType[int]] = None


class ModifyFtueCounter_SharplaAudit(BaseModel):
    """Category: audit_event. Base: SharplaCmdAudit"""

    counter_id: Optional[int] = None
    changeDelta: Optional[int] = None
    resetToZero: Optional[bool] = None
    resetToZeroAndApplyDelta: Optional[bool] = None


class Nudge_Req(BaseModel):
    """Category: request. Base: RakshaItem"""

    clide: Optional[str] = None
    beatmap_id: Optional[int] = None
    emoji_id: Optional[int] = None
    score: Optional[Any] = None
    beatmapVersion: Optional[int] = None


class Nudge_Resp(BaseModel):
    """Category: response. Base: RakshaItem"""

    id: Optional[str] = None


class OfferAd_SharplaAudit(BaseModel):
    """Category: audit_event. Base: SharplaCmdAudit"""

    pass


class OpenBonusCardsRewardGachaBox_SharplaAudit(BaseModel):
    """Category: audit_event. Base: SharplaCmdAudit"""

    ChoiceIndex: Optional[int] = None


class OpenCampaignGachaBox_SharplaAudit(BaseModel):
    """Category: audit_event. Base: SharplaCmdAudit"""

    slotTemplate_id: Optional[int] = None


class PayToForceOpenCampaignGachaBox_SharplaAudit(BaseModel):
    """Category: audit_event. Base: SharplaCmdAudit"""

    slotTemplate_id: Optional[int] = None


class PurchasingRefreshAfterAlloc_SharplaAudit(BaseModel):
    """Category: audit_event. Base: SharplaCmdAudit"""

    pass


class QuestionnaireQuestionAnswer(BaseModel):
    """Category: data_model. Base: RakshaItem"""

    question_id: Optional[int] = None
    answerIndexes: Optional[ListType[int]] = None


class RefreshBonusCardsSystem_SharplaAudit(BaseModel):
    """Category: audit_event. Base: SharplaCmdAudit"""

    pass


class RemoveFriend_Req(BaseModel):
    """Category: request. Base: RakshaItem"""

    clide: Optional[str] = None
    socialSource: Optional[str] = None


class RemoveFriend_Resp(BaseModel):
    """Category: response. Base: RakshaItem"""

    pass


class RemoveSeenStringDatedRooster_SharplaAudit(BaseModel):
    """Category: audit_event. Base: SharplaCmdAudit"""

    query: Optional[str] = None
    openEnded: Optional[bool] = None
    queries: Optional[ListType[str]] = None


class RenamePlayerName_SharplaRpcReq(BaseModel):
    """Category: request. Base: SharplaRpcRequest"""

    name: Optional[str] = None


class RenamePlayerName_SharplaRpcResp(BaseModel):
    """Category: response. Base: SharplaRpcResponse"""

    allowed: Optional[bool] = None


class RequestHeader(BaseModel):
    """Category: header. Base: RakshaItem"""

    pass


class ResponseHeader(BaseModel):
    """Category: header. Base: RakshaItem"""

    pass


class RhythmGameEnded_SharplaAudit(BaseModel):
    """Category: audit_event. Base: SharplaCmdAudit"""

    song_id: Optional[int] = None
    maxStreak: Optional[int] = None
    numContinues: Optional[int] = None
    scoreTypeCounts: Optional[ListType[Any]] = None
    checkpointReached: Optional[int] = None
    resultType: Optional[Any] = None
    interactionTypeAndCountPerStreakMultiplier: Optional[ListType[Any]] = None
    maxStreakMultiplier: Optional[float] = None
    previousBeatmapLeaderboardRank: Optional[int] = None
    currentBeatmapLeaderboardRank: Optional[int] = None
    score: Optional[Any] = None
    numOfLateOkScoreTypes: Optional[int] = None
    currentBeatmapLeaderboardNumEntries: Optional[int] = None
    numOfTooEarlyScores: Optional[int] = None
    numOfMissTaps: Optional[int] = None
    showdownSongRank: Optional[int] = None
    showdownOverallRank: Optional[int] = None
    videoAdSystemActive: Optional[bool] = None
    touchBugAnalyticsData: Optional[Any] = None
    associatedLiveOpsEvent_id: Optional[int] = None
    deluxeInteractionScores: Optional[Any] = None
    eventPoints: Optional[int] = None


class RhythmGameIntro_SharplaAudit(BaseModel):
    """Category: audit_event. Base: SharplaCmdAudit"""

    song_id: Optional[int] = None


class RhythmGameStarted_SharplaAudit(BaseModel):
    """Category: audit_event. Base: SharplaCmdAudit"""

    song_id: Optional[int] = None
    uniqueId: Optional[str] = None
    audioOutputType: Optional[Any] = None
    audioVolume: Optional[float] = None
    vibration: Optional[bool] = None
    calibrationOffset: Optional[float] = None
    numFriends: Optional[int] = None
    currentBeatmapLeaderboardRank: Optional[int] = None
    currentBeatmapLeaderboardNumEntries: Optional[int] = None
    bluetoothOutputName: Optional[str] = None
    currentOverallLeaderboardScore: Optional[int] = None
    associatedLiveOpsEvent_id: Optional[int] = None
    songSelectSource: Optional[Any] = None
    songSelectShuffleForwardCount: Optional[int] = None
    songSelectShuffleBackwardCount: Optional[int] = None


class ScoreInShowdown_Req(BaseModel):
    """Category: request. Base: RakshaItem"""

    score: Optional[int] = None
    roomId: Optional[str] = None
    beatmap_id: Optional[int] = None


class ScoreInShowdown_Resp(BaseModel):
    """Category: response. Base: RakshaItem"""

    pass


class ScoreTypeAndCount(BaseModel):
    """Category: data_model. Base: RakshaItem"""

    scoreType: Optional[Any] = None
    count: Optional[int] = None


class SearchPlayersByName_Req(BaseModel):
    """Category: request. Base: RakshaItem"""

    name: Optional[str] = None


class SearchPlayersByName_Resp(BaseModel):
    """Category: response. Base: RakshaItem"""

    players: Optional[ListType[Any]] = None
    isError: Optional[bool] = None


class Season_BuyLevel_SharplaAudit(BaseModel):
    """Category: audit_event. Base: SharplaCmdAudit"""

    numLevels: Optional[int] = None


class Season_ClaimLevel_SharplaAudit(BaseModel):
    """Category: audit_event. Base: SharplaCmdAudit"""

    levelIndex: Optional[int] = None
    premiumReward: Optional[bool] = None


class Season_UpdateSeason_SharplaAudit(BaseModel):
    """Category: audit_event. Base: SharplaCmdAudit"""

    pass


class SelectFtueStarterSong_SharplaAudit(BaseModel):
    """Category: audit_event. Base: SharplaCmdAudit"""

    Beatmap_id: Optional[int] = None


class SetActiveVideoAdsProfile_SharplaAudit(BaseModel):
    """Category: audit_event. Base: SharplaCmdAudit"""

    profile_id: Optional[str] = None


class SetAllowVideoAdsFreeGems_SharplaAudit(BaseModel):
    """Category: audit_event. Base: SharplaCmdAudit"""

    allowVideoAdsFreeGems: Optional[bool] = None
    shopItemTemplate_id: Optional[int] = None


class SetAppleMusicPlaylistId_SharplaAudit(BaseModel):
    """Category: audit_event. Base: SharplaCmdAudit"""

    playlistId: Optional[str] = None


class SetCallingCard_SharplaAudit(BaseModel):
    """Category: audit_event. Base: SharplaCmdAudit"""

    callingCard_id: Optional[int] = None


class SetFtueFlag_SharplaAudit(BaseModel):
    """Category: audit_event. Base: SharplaCmdAudit"""

    Flag_id: Optional[int] = None
    Value: Optional[bool] = None


class SetGlobalTrackSkin_SharplaAudit(BaseModel):
    """Category: audit_event. Base: SharplaCmdAudit"""

    trackSkin_id: Optional[int] = None


class SetGooglePlayGroupingToken_Req(BaseModel):
    """Category: request. Base: RakshaItem"""

    token: Optional[str] = None


class SetGooglePlayGroupingToken_Resp(BaseModel):
    """Category: response. Base: RakshaItem"""

    pass


class SetHasSeenBonusCardsReward_SharplaAudit(BaseModel):
    """Category: audit_event. Base: SharplaCmdAudit"""

    pass


class SetPerfectPlusColourOverride_SharplaAudit(BaseModel):
    """Category: audit_event. Base: SharplaCmdAudit"""

    ColourOverride_id: Optional[int] = None


class SetPlayerCustomisation_SharplaAudit(BaseModel):
    """Category: audit_event. Base: SharplaCmdAudit"""

    Data: Optional[Any] = None


class SetPlayerName_SharplaAudit(BaseModel):
    """Category: audit_event. Base: SharplaCmdAudit"""

    name: Optional[str] = None


class SetPlayerName_SharplaRpcReq(BaseModel):
    """Category: request. Base: SharplaRpcRequest"""

    name: Optional[str] = None


class SetPlayerName_SharplaRpcResp(BaseModel):
    """Category: response. Base: SharplaRpcResponse"""

    allowed: Optional[bool] = None


class SetProfileIcon_SharplaAudit(BaseModel):
    """Category: audit_event. Base: SharplaCmdAudit"""

    profileIcon_id: Optional[int] = None


class SetPromoInterstitialSeen_SharplaAudit(BaseModel):
    """Category: audit_event. Base: SharplaCmdAudit"""

    PromoInterstitial_id: Optional[int] = None


class SetSelectedSong_SharplaAudit(BaseModel):
    """Category: audit_event. Base: SharplaCmdAudit"""

    song_id: Optional[int] = None
    medalChaseMode: Optional[bool] = None
    songSelectionSourceType: Optional[Any] = None


class SetShopItemAlertShownDate_SharplaAudit(BaseModel):
    """Category: audit_event. Base: SharplaCmdAudit"""

    shopItemId: Optional[int] = None
    timeMsecs: Optional[int] = None


class SetStatusForLeaderboardEvent_SharplaAudit(BaseModel):
    """Category: audit_event. Base: SharplaCmdAudit"""

    game_id: Optional[int] = None
    status: Optional[Any] = None


class SetVideoAdsConsentGiven_SharplaAudit(BaseModel):
    """Category: audit_event. Base: SharplaCmdAudit"""

    videoAdsConsentGiven: Optional[Any] = None


class Share_Req(BaseModel):
    """Category: request. Base: RakshaItem"""

    beatmap_id: Optional[int] = None
    emoji_id: Optional[int] = None
    score: Optional[Any] = None


class Share_Resp(BaseModel):
    """Category: response. Base: RakshaItem"""

    id: Optional[str] = None


class SharplaGameCmdHeader(BaseModel):
    """Category: header. Base: SharplaCmdHeader"""

    hardCurrency: Optional[int] = None
    softCurrency: Optional[int] = None
    randomSeeds: Optional[int] = None
    numSongs: Optional[int] = None
    lastUnlockedSong_id: Optional[int] = None
    totalSongScore: Optional[float] = None
    saveCount_deprecated: Optional[int] = None


class ShopSystemRefresh_SharplaAudit(BaseModel):
    """Category: audit_event. Base: SharplaCmdAudit"""

    pass


class ShowdownPlayerEntry(BaseModel):
    """Category: data_model. Base: RakshaItem"""

    clide: Optional[str] = None
    scores: Optional[ListType[Any]] = None
    joinedTimeMsecs: Optional[int] = None
    status: Optional[Any] = None
    skillPercent3dp: Optional[int] = None


class ShowdownPlayerScore(BaseModel):
    """Category: data_model. Base: RakshaItem"""

    beatmap_id: Optional[int] = None
    score: Optional[int] = None


class ShowdownPlayerStatus(BaseModel):
    """Category: data_model. Base: RakshaItem"""

    emote_id: Optional[int] = None
    gameStartedTimeMsecs: Optional[int] = None
    emotedTimeMsecs: Optional[int] = None


class ShowdownTO(BaseModel):
    """Category: data_model. Base: RakshaItem"""

    endTimeMsecs: Optional[int] = None
    players: Optional[ListType[Any]] = None
    id: Optional[str] = None
    bucket_id: Optional[int] = None


class SkipOpeningOfCampaignGachaBox_SharplaAudit(BaseModel):
    """Category: audit_event. Base: SharplaCmdAudit"""

    slotTemplate_id: Optional[int] = None


class StartAdWatch_SharplaAudit(BaseModel):
    """Category: audit_event. Base: SharplaCmdAudit"""

    AdInProgress: Optional[Any] = None


class StartCountdownOnCampaignGachaBox_SharplaAudit(BaseModel):
    """Category: audit_event. Base: SharplaCmdAudit"""

    slotTemplate_id: Optional[int] = None
    speedupForVideoAd: Optional[bool] = None


class StartIAPPurchase_SharplaAudit(BaseModel):
    """Category: audit_event. Base: SharplaCmdAudit"""

    purchaseData: Optional[Any] = None


class StartSharplaSessionRequest(BaseModel):
    """Category: request. Base: StartSessionRequest"""

    session: Optional[Any] = None
    analytics_device: Optional[Any] = None
    analytics_attribution: Optional[Any] = None
    analytics_testing: Optional[ListType[Any]] = None
    cheatClientCountryCode: Optional[str] = None
    updatedCountryCode: Optional[str] = None
    forceNameChange: Optional[Any] = None
    currentPlayerLocationCountryCode: Optional[str] = None
    appValidationData: Optional[str] = None


class SyncReq(BaseModel):
    """Category: data_model. Base: RakshaItem"""

    startRequest: Optional[Any] = None
    langConfigVersion: Optional[str] = None
    gameConfigVersion: Optional[str] = None
    songConfigVersion: Optional[str] = None
    callingCardConfigVersion: Optional[str] = None
    liveOpsProfileIconConfigVersion: Optional[str] = None
    liveOpsTrackSkinConfigVersion: Optional[str] = None
    liveOpsEmojiConfigVersion: Optional[str] = None


class SyncResp(BaseModel):
    """Category: data_model. Base: RakshaItem"""

    profile: Optional[Any] = None
    hasClaimableRewards: Optional[bool] = None
    playerHubStatus: Optional[int] = None
    newsFeedConfig: Optional[Any] = None
    liveOpsBundleConfig: Optional[Any] = None
    liveOpsDeeplinkRewardConfig: Optional[Any] = None
    liveOpsEventConfig: Optional[Any] = None
    liveOpsSeasonConfig: Optional[Any] = None
    liveOpsLoadingScreenConfig: Optional[Any] = None


class SyncShowdown_Req(BaseModel):
    """Category: request. Base: RakshaItem"""

    roomId: Optional[str] = None


class SyncShowdown_Resp(BaseModel):
    """Category: response. Base: RakshaItem"""

    showdown: Optional[Any] = None


class UpdateAttribution_SharplaAudit(BaseModel):
    """Category: audit_event. Base: SharplaCmdAudit"""

    campaign: Optional[str] = None
    creative: Optional[str] = None
    adset: Optional[str] = None
    setCampaign: Optional[bool] = None
    setCreative: Optional[bool] = None
    setAdset: Optional[bool] = None


class UpdateEventTotaliserVideoAds_SharplaAudit(BaseModel):
    """Category: audit_event. Base: SharplaCmdAudit"""

    pass


class UpdateLikedBeatmaps_SharplaAudit(BaseModel):
    """Category: audit_event. Base: SharplaCmdAudit"""

    toAdd_id: Optional[ListType[int]] = None
    toRemove_id: Optional[ListType[int]] = None


class UpdateShopIAPState_SharplaAudit(BaseModel):
    """Category: audit_event. Base: SharplaCmdAudit"""

    ForShopItem_id: Optional[int] = None


class UpdateShopSystems_SharplaAudit(BaseModel):
    """Category: audit_event. Base: SharplaCmdAudit"""

    pass


class UseFriendInviteToken_Req(BaseModel):
    """Category: request. Base: RakshaItem"""

    token: Optional[str] = None


class UseFriendInviteToken_Resp(BaseModel):
    """Category: response. Base: RakshaItem"""

    pass


class WatchAdTotaliserAd_SharplaAudit(BaseModel):
    """Category: audit_event. Base: SharplaCmdAudit"""

    pass
