import torch
import torch.nn as nn
from mir_eval.separation import bss_eval_sources


def validate(audio, model, embedder, testloader, writer, step):
    model.eval()

    criterion = nn.MSELoss()
    with torch.no_grad():
        for batch in testloader:
            dvec_mel, target_wav, mixed_wav, target_mag, mixed_mag, mixed_phase = batch[0]

            dvec_mel = dvec_mel.cuda()
            target_mag = target_mag.unsqueeze(0).cuda()
            mixed_mag = mixed_mag.unsqueeze(0).cuda()  # (1, 601, 301)
            mixed_phase = mixed_phase.cuda()
            dvec = embedder(dvec_mel)
            dvec = dvec.unsqueeze(0)
            purify_mask = model(mixed_mag, dvec)
            audio_mask = audio.tensorspec2wav(purify_mask[0, :, :], mixed_phase)  # eliminate batch dim
            mixed_wav = torch.from_numpy(mixed_wav).float().cuda()
            denoised_wav = audio_mask + mixed_wav
            denoised_mag = audio.tensorwav2spec(denoised_wav)
            denoised_mag = denoised_mag.unsqueeze(0)
            test_loss = criterion(denoised_mag, target_mag).item()
            mixed_mag = mixed_mag[0].cpu().detach().numpy()
            target_mag = target_mag[0].cpu().detach().numpy()
            purify_mask = purify_mask[0].cpu().detach().numpy()
            denoised_wav = denoised_wav.cpu().detach().numpy()
            denoised_mag = denoised_mag[0].cpu().detach().numpy()
            audio_mask = audio_mask.cpu().detach().numpy()
            sdr = bss_eval_sources(target_wav, denoised_wav, False)[0][0]
            writer.log_evaluation(test_loss, sdr,
                                  mixed_wav, target_wav, audio_mask, denoised_wav,
                                  mixed_mag.T, target_mag.T, purify_mask.T, denoised_mag.T,
                                  step)
            break

    model.train()
