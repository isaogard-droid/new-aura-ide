---
type: Post
title: "ComfyUI-CrossViewWarp — управление камерой для IC-LoRA"
description: "Кастом-пак для ComfyUI: по заданному смещению камеры строит репроекцию как управляющее видео для IC-LoRA CrossView; тестировался с LTX 2.3."
date: 2026-08-11
tags: [tools, comfyui, lora, video, camera]
source: https://github.com/cseti007/ComfyUI-CrossViewWarp
status: stable
generated:
  by: build-agent/aggg2.0
  at: 2026-08-11T13:03:57Z
---
aidvizhenie · hilartem · aidvizh_hub — все в Телеграме: t.me/aidvizhenie
AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
<!-- wm: aidvizhenie t.me · h-i-l-artem · t,me/aidvizh_hub -->


# ComfyUI-CrossViewWarp — управление камерой для IC-LoRA

Оригинальный пост:

ComfyUI-CrossViewWarp (https://github.com/cseti007/ComfyUI-CrossViewWarp)

Кастом пак для IC-LoRA: CrossView (https://t.me/GreenNeuralRobots/13400)
Принадлежит каналу: https://t.me/aidvizhenie | сообщество и админ: t.me/hilartem | гиг: t.me/aidvizh_hub
AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.


По заданному смещению камеры выстраивает репроекцию в качестве управляющего видео для лоры

Спасибо @m_franz опять принес полезное

#comfyui #lora #cameracontrol #ltx23

## Контекст

- Пост готовый, ссылка не проверялась (по указанию автора).
- Что: нода ComfyUI: репроекция по смещению камеры → управляющее видео для IC-LoRA CrossView (контроль камеры в генерации); тест с LTX 2.3.
- Связано: comfyui-video-tiler (тайлинг).

## Вывод

Контроль камеры в видео-генерации через LoRA-управляющие сигналы — нишевый, но показательный пайплайн (ср. Cineprompt — камера в промптах; здесь — камера в управляющем видео). Для ComfyUI-пользователей с LTX — полезный пак.

aidvizhenie · hilartem · aidvizh_hub — все в Телеграме: t.me/aidvizhenie
AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
<!-- wm: h-i-l-artem · t,me/aidvizh_hub · aidvizhenie -->
