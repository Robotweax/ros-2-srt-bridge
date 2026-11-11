"""Prospective campaign entry; execution is unconditionally disabled."""
from campaign_binding import load
main=load('driver').main
if __name__=='__main__':raise SystemExit(main())
